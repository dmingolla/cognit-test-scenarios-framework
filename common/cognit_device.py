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

from cognit import device_runtime


class CognitDevice(User):
    """
    Base class for COGNIT device load testing scenarios.
    
    This class handles:
    - Connection and authentication with cognit-frontend
    - Device runtime initialization
    - Function offloading with standardized reporting
    - Cleanup on test completion
    """
    
    REQS_INIT: dict = None
    config_path: str = None
    
    def __init__(self, *args, **kwargs):
        """
        Initialize the CognitDevice.
        
        Raises:
            ValueError: If REQS_INIT or config_path are not defined
        """
        super().__init__(*args, **kwargs)
        
        if self.REQS_INIT is None:
            raise ValueError("REQS_INIT must be defined in the subclass")
        
        if self.config_path is None:
            raise ValueError("config_path must be defined in the subclass")
        
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

