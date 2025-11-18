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
                
                assigned_id = self.__class__._available_pool.pop(0)
                self.REQS_INIT["ID"] = assigned_id
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
        
        try:
            result = self.device_runtime.call(function, *args, timeout=timeout)
            response_time = int((time.time() - start_time) * 1000)
            
            events.request.fire(
                request_type="offload",
                name=f"{function.__name__}",
                response_time=response_time,
                response_length=len(str(result)) if result is not None else 0,
                exception=None,
                context={}
            )
            
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
            return None
    
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

