"""
Heavy Load Scenario - High frequency, intensive computations.
Tests performance under heavy computational load with matrix multiplications.
"""

import os
from common.cognit_device import CognitDevice
from locust import task, between


def matrix_multiplication(size: int, iterations: int):
    """Perform intensive matrix multiplications."""
    import random
    
    result_sum = 0
    for _ in range(iterations):
        # Create random matrices
        matrix_a = [[random.random() for _ in range(size)] for _ in range(size)]
        matrix_b = [[random.random() for _ in range(size)] for _ in range(size)]
        
        # Perform matrix multiplication
        result = [[0 for _ in range(size)] for _ in range(size)]
        for i in range(size):
            for j in range(size):
                for k in range(size):
                    result[i][j] += matrix_a[i][k] * matrix_b[k][j]
        
        # Sum all elements in result matrix
        result_sum += sum(sum(row) for row in result)
    
    return result_sum


class HeavyLoadScenario(CognitDevice):
    """
    Heavy load scenario with intensive computational requirements.
    Simulates high-performance computing workloads with matrix operations.
    """
    randomize_device_id = True
    
    REQS_INIT = {
        "ID": "device-high-load",
        "FLAVOUR": "GlobalOptimizer",
        #"IS_CONFIDENTIAL": False,
        "PROVIDERS": ["provider_1"],
        "GEOLOCATION": {
            "latitude": 59.3294,
            "longitude": 18.0687
        }
    }
    
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "cognit-config.yml")
    
    @task
    def offload_heavy_task(self):
        """Offload heavy matrix computation."""
        result = self.offload_function(matrix_multiplication, 100, 5)
        print("-----------------------------------------------")
        print(f"Device ID: {self.REQS_INIT['ID']}, Flavour: {self.REQS_INIT['FLAVOUR']}, result: {result}")
        print("-----------------------------------------------")

