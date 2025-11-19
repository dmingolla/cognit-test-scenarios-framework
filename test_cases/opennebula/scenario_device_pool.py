"""
Device Pool Scenario - Fixed device IDs for historical metrics tracking.
Tests performance with a predefined set of device IDs to enable tracking metrics over time.
Each device ID is assigned exactly once, allowing historical comparison across test runs.
"""

import os
from common.cognit_device import CognitDevice
from locust import task, between


def compute_metrics(duration: int):
    """Simulate computation that generates metrics for tracking."""
    import time
    import random
    
    end_time = time.time() + duration
    operations = 0
    
    while time.time() < end_time:
        # Simulate some computation
        x = random.random()
        y = random.random()
        result = x * y
        operations += 1
    
    return {
        "operations": operations,
        "duration": duration,
        "avg_throughput": operations / duration if duration > 0 else 0
    }


class DevicePoolScenario(CognitDevice):
    """
    Device pool scenario with fixed device IDs for historical metrics tracking.
    
    This scenario uses a predefined pool of 10 device IDs. Each Locust user
    gets assigned exactly one unique device ID from the pool. This allows
    tracking metrics for the same devices across multiple test runs.
    
    IMPORTANT: The number of users must exactly match the pool size (10).
    Use: locust -f scenario_device_pool.py --headless --users 10 --spawn-rate 2
    """
    # Define fixed pool of 10 device IDs with unique requirements
    device_id_pool = []
    for i in range(1, 11):
        device_id = f"device-pool-{i:02d}"
        # Alternate flavors: Odd=GlobalOptimizer, Even=HighPerformance
        flavour = "GlobalOptimizer" if i % 2 != 0 else "HighPerformance"
        # Shift latitude slightly for each device
        lat = 41.3851 + (i * 0.01)
        
        reqs = {
            "ID": device_id,
            "FLAVOUR": flavour,
            "IS_CONFIDENTIAL": False,
            "PROVIDERS": ["provider_1"],
            "GEOLOCATION": {
                "latitude": round(lat, 4),
                "longitude": 2.1734
            }
        }
        device_id_pool.append(reqs)
    
    # Pool-based scenarios automatically disable randomization
    randomize_device_id = False
    
    REQS_INIT = {
        "ID": "device-pool-default",  # Will be overridden by pool assignment
        "FLAVOUR": "GlobalOptimizer",
        "IS_CONFIDENTIAL": False,
        "PROVIDERS": ["provider_1"],
        "GEOLOCATION": {
            "latitude": 41.3851,
            "longitude": 2.1734
        }
    }
    
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "cognit-config.yml")
    wait_time = between(2, 4)
    
    @task
    def offload_metrics_task(self):
        """Offload computation task and track metrics."""
        result = self.offload_function(compute_metrics, 2)
        print("-----------------------------------------------")
        print(f"Device ID: {self.REQS_INIT['ID']}, Flavour: {self.REQS_INIT['FLAVOUR']}, Metrics: {result}")
        print("-----------------------------------------------")

