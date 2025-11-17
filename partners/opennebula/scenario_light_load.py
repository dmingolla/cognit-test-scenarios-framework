"""
Light Load Scenario - Low frequency, small computations.
Tests baseline performance with minimal load.
"""

import os
from common.cognit_device import CognitDevice
from locust import task, between


def light_computation(duration: int):
    """Simple computation with low CPU usage."""
    import time
    import random
    
    end_time = time.time() + duration
    result = 0
    
    while time.time() < end_time:
        x = random.random()
        for _ in range(1):
            result += 1
    return result


class LightLoadScenario(CognitDevice):
    """
    Light load scenario with minimal computational requirements.
    Simulates IoT devices with occasional light processing.
    """
    
    REQS_INIT = {
        "ID": "device-light-01",
        "FLAVOUR": "GlobalOptimizer",
        "IS_CONFIDENTIAL": False,
        "PROVIDERS": ["provider_1"],
        "GEOLOCATION": {
            "latitude": 41.3851,
            "longitude": 2.1734
        }
    }
    
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "cognit-config.yml")
    wait_time = between(3, 5)
    
    @task
    def offload_light_task(self):
        """Offload light computation."""
        result = self.offload_function(light_computation, 1)
        print("-----------------------------------------------")
        print(f"Flavour: {self.REQS_INIT['FLAVOUR']}, result: {result}")
        print("-----------------------------------------------")

