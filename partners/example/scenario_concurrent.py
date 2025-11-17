"""
Minimal example scenario for COGNIT load testing.

This scenario demonstrates how to create a simple load test using the CognitDevice base class.
It offloads a CPU stress function and measures the performance.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common.cognit_device import CognitDevice
from locust import task, between


def stress(duration: int):
    """
    Simple CPU stress function that runs for a specified duration.
    
    Args:
        duration: Duration in seconds to run the stress test
    
    Returns:
        int: Number of iterations completed
    """
    import time
    import random

    end_time = time.time() + duration
    result = 0

    while time.time() < end_time:
        x = random.random()
        for _ in range(1):
            result += 1
    return result


class ConcurrentStressScenario(CognitDevice):
    """
    Example scenario that demonstrates concurrent CPU stress offloading.
    
    This scenario:
    - Defines device requirements (REQS_INIT)
    - Specifies the cognit configuration file path
    - Implements a task that offloads the stress function
    - Uses Locust's wait_time to control request rate
    """
    
    REQS_INIT = {
        "ID": "device-ICE",
        "FLAVOUR": "GlobalOptimizer",
        "IS_CONFIDENTIAL": True,
        "PROVIDERS": ["provider_1"],
        "GEOLOCATION": {
            "latitude": 52.2294,
            "longitude": 21.0113
        }
    }
    
    config_path = os.path.join(os.path.dirname(__file__), "cognit-config.yml")
    wait_time = between(1, 3)
    
    @task
    def offload_stress_function(self):
        """
        Task that offloads the stress function to COGNIT platform.
        
        This method will be called repeatedly by Locust based on the task weight
        and wait_time configuration.
        """
        result = self.offload_function(stress, 1)
        
        if result is not None:
            print(f"Stress function completed, result: {result}")
        else:
            print("Stress function failed or returned None")


