"""
Base class for COGNIT load testing scenarios using Locust.

Partners should inherit from this class and define:
- REQS_INIT: Dictionary with device requirements (ID, FLAVOUR, etc.)
- config_path: Path to cognit configuration YAML file
- Tasks using @task decorator that call self.offload_function()
"""

from locust import User, events
from typing import Callable, Any, Optional
import sys
import os
import time
import copy
import uuid
import threading
import traceback
import json
import hashlib
from datetime import datetime

from common.metrics_logger import MetricsLogger

from cognit import device_runtime


def _validate_device_pool(environment, **kwargs):
    """
    Validate that user count matches device ID pool size when pool is defined.
    Called automatically by Locust before test starts.
    """
    # Find all CognitDevice subclasses that have a device_id_pool defined
    for user_class in environment.runner.user_classes:
        if issubclass(user_class, CognitDevice) and user_class.device_id_pool is not None:
            pool_size = len(user_class.device_id_pool)
            num_users = environment.runner.target_user_count
            
            if num_users != pool_size:
                error_msg = (
                    f"Device ID pool has {pool_size} IDs but {num_users} users specified. "
                    f"They must match. Use --users {pool_size} to run this scenario."
                )
                print(f"ERROR: {error_msg}")
                environment.runner.quit()
                raise ValueError(error_msg)


def _reset_device_pool(environment, **kwargs):
    """
    Reset device ID pools after test completes so they can be reused in subsequent runs.
    Called automatically by Locust after test stops.
    """
    for user_class in environment.runner.user_classes:
        if issubclass(user_class, CognitDevice) and user_class.device_id_pool is not None:
            with user_class._pool_lock:
                user_class._available_pool = None  # Reset so it reinitializes on next run


# Register validation and reset hooks
events.test_start.add_listener(_validate_device_pool)
events.test_stop.add_listener(_reset_device_pool)


class CognitDevice(User):
    """
    Base class for COGNIT device load testing scenarios.
    
    This class handles:
    - Connection and authentication with cognit-frontend
    - Device runtime initialization
    - Function offloading with standardized reporting
    - Cleanup on test completion
    """
    
    abstract = True
    
    REQS_INIT: dict = None
    config_path: str = None
    randomize_device_id: bool = True  # Set to False to use the same device ID for all users
    device_id_pool: list = None  # Optional: Fixed list of device IDs to assign (one per user)
    
    # Thread-safe pool management
    _pool_lock = threading.Lock()
    _available_pool: list = None  # Tracks remaining IDs from the pool
    
    # Metrics Logger
    _metrics_logger = MetricsLogger()
    
    # Generate a unique session ID for this process execution
    # This ensures all devices in this run share a common identifier base
    _session_id = str(uuid.uuid4())[:8]

    @property
    def run_id(self):
        """
        Generate a deterministic Run ID for this scenario execution.
        Combines the process-level session ID with the Scenario Class Name.
        Ensures all devices in the same scenario share the same Run ID.
        """
        unique_string = f"{self._session_id}_{self.__class__.__name__}"
        return hashlib.md5(unique_string.encode()).hexdigest()

    def __init__(self, *args, **kwargs):
        """
        Initialize the CognitDevice.
        
        Each Locust user gets a unique instance with its own REQS_INIT.
        If randomize_device_id is True, each user will have a unique device ID.
        
        Raises:
            ValueError: If REQS_INIT or config_path are not defined
        """
        super().__init__(*args, **kwargs)
        
        if self.REQS_INIT is None:
            raise ValueError("REQS_INIT must be defined in the subclass")
        
        if self.config_path is None:
            raise ValueError("config_path must be defined in the subclass")
        
        # Create a deep copy of REQS_INIT for this user instance
        # This ensures each user has its own independent configuration
        self.REQS_INIT = copy.deepcopy(self.__class__.REQS_INIT)
        
        # Initialize device ID pool if defined (only once at class level)
        if self.__class__.device_id_pool is not None:
            with self.__class__._pool_lock:
                # Initialize available pool on first access
                if self.__class__._available_pool is None:
                    self.__class__._available_pool = list(self.__class__.device_id_pool)
                
                # Assign device ID from pool and remove it (thread-safe)
                if len(self.__class__._available_pool) == 0:
                    raise ValueError(
                        f"Device ID pool exhausted. All {len(self.__class__.device_id_pool)} IDs have been assigned."
                    )
                
                assigned_item = self.__class__._available_pool.pop(0)
                
                if isinstance(assigned_item, dict):
                    # It's a full config object, use it to override REQS_INIT
                    self.REQS_INIT = copy.deepcopy(assigned_item)
                    if "ID" not in self.REQS_INIT:
                        raise ValueError("Device pool items must contain an 'ID' field")
                else:
                    raise ValueError("Device pool items must be a dictionary")
        # Randomize device ID if enabled (existing behavior preserved)
        elif self.randomize_device_id:
            base_id = self.REQS_INIT.get("ID", "device")
            # Generate a unique ID using UUID (short version)
            unique_suffix = str(uuid.uuid4())[:8]
            self.REQS_INIT["ID"] = f"{base_id}-{unique_suffix}"
        
        self.device_runtime: Optional[device_runtime.DeviceRuntime] = None
    
    def on_start(self):
        """
        Initialize the device runtime when a Locust user starts.
        Called automatically by Locust before tasks are executed.
        """
        try:
            self.device_runtime = device_runtime.DeviceRuntime(self.config_path)
            success = self.device_runtime.init(self.REQS_INIT)
            
            if not success:
                events.request.fire(
                    request_type="init",
                    name="device_runtime_init",
                    response_time=0,
                    response_length=0,
                    exception=Exception("Failed to initialize device runtime"),
                    context={}
                )
                raise Exception("Failed to initialize device runtime")
            
        except Exception as e:
            events.request.fire(
                request_type="init",
                name="device_runtime_init",
                response_time=0,
                response_length=0,
                exception=e,
                context={}
            )
            raise
    
    def offload_function(self, function: Callable, *args, timeout: Optional[int] = None, **kwargs) -> Any:
        """
        Offload a function to the COGNIT platform.
        
        This is a helper method that wraps device_runtime.call() and provides
        standardized success/failure reporting to Locust.

        We log the request information to the database for later analysis.
        
        Args:
            function: The function to offload
            *args: Positional arguments to pass to the function
            timeout: Optional timeout in seconds
            **kwargs: Keyword arguments (currently not used, reserved for future use)
        
        Returns:
            The result from the offloaded function, or None if execution failed
        
        Example:
            result = self.offload_function(stress_function, duration=5)
        """
        if self.device_runtime is None:
            events.request.fire(
                request_type="offload",
                name=f"{function.__name__}",
                response_time=0,
                response_length=0,
                exception=Exception("Device runtime not initialized"),
                context={}
            )
            return None
        
        start_time = time.time()
        
        # Capture request arguments for logging
        app_reqs_json = None
        try:
            # Create a dictionary of arguments to store
            req_data = {
                "device_requirements": self.REQS_INIT
            }
            # Convert to JSON string, handling potential serialization issues gracefully
            app_reqs_json = json.dumps(req_data, default=str)
        except Exception as e:
            print(f"Warning: Failed to serialize request args: {e}")
            app_reqs_json = "{}"
        
        try:
            result = self.device_runtime.call(function, *args, timeout=timeout)
            response_time = int((time.time() - start_time) * 1000)
            
            # Check for execution error in result object
            status = "SUCCESS"
            error_msg = None
            
            # First check if result is None
            if result is None:
                status = "FAILURE"
                error_msg = "Check the Locust logs for more details. Most likely, no backend available for the requested flavor/requirements"

            # Check if result has ret_code attribute
            elif hasattr(result, "ret_code"):
                try:
                    # Handle potential Enum or integer
                    ret_code_val = result.ret_code.value if hasattr(result.ret_code, "value") else int(result.ret_code)
                    
                    if ret_code_val != 0:
                        status = "FAILURE"
                        error_msg = str(getattr(result, "err", "Unknown execution error"))
                except Exception as e:
                    print(f"Warning: Failed to parse ret_code: {e}")

            if status == "SUCCESS":
                events.request.fire(
                    request_type="offload",
                    name=f"{function.__name__}",
                    response_time=response_time,
                    response_length=len(str(result)) if result is not None else 0,
                    exception=None,
                    context={}
                )
                # Log success metric to SQLite
                self._log_to_db(function.__name__, "SUCCESS", response_time, result, app_reqs_json=app_reqs_json)
            else:
                events.request.fire(
                    request_type="offload",
                    name=f"{function.__name__}",
                    response_time=response_time,
                    response_length=0,
                    exception=Exception(error_msg),
                    context={}
                )
                # Log failure metric to SQLite
                self._log_to_db(function.__name__, "FAILURE", response_time, result, error_msg=error_msg, app_reqs_json=app_reqs_json)
            return result
            
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            
            events.request.fire(
                request_type="offload",
                name=f"{function.__name__}",
                response_time=response_time,
                response_length=0,
                exception=e,
                context={}
            )
            
            # Log failure metric to SQLite
            self._log_to_db(function.__name__, "FAILURE", response_time, None, error_msg=str(e), app_reqs_json=app_reqs_json)
            
            return None
    
    def _log_to_db(self, task_name, status, latency, result=None, error_msg=None, app_reqs_json=None):
        """Helper to log metrics to SQLite."""
        metric_val = None
        
        # Try to extract a numeric metric value if result is a dict or number
        if isinstance(result, dict):
            # Look for common metric keys
            for key in ["operations", "throughput", "cpu", "latency"]:
                if key in result and isinstance(result[key], (int, float)):
                    metric_val = result[key]
                    break
        elif isinstance(result, (int, float)):
            metric_val = result
            
        self._metrics_logger.log_metric(
            run_id=self.run_id,
            scenario_name=self.__class__.__name__,
            device_id=self.REQS_INIT["ID"],
            task_name=task_name,
            status=status,
            latency_ms=latency,
            metric_value=metric_val,
            error_msg=error_msg,
            app_reqs_json=app_reqs_json
        )

    def on_stop(self):
        """
        Cleanup when a Locust user stops.
        Called automatically by Locust after all tasks are completed.
        """
        if self.device_runtime is not None:
            try:
                self.device_runtime.stop()
            except Exception as e:
                print(f"Warning: Error during device runtime cleanup: {e}")
            finally:
                self.device_runtime = None

