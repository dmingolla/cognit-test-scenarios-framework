"""
Energy Carbon Efficiency Scenario
Each device uses stress-ng to generate controlled CPU workloads for measuring power consumption.

Workflow:
1. When you run Locust with this scenario, it spawns multiple "users" (simulated devices)
2. Each user gets assigned a unique device ID from the predefined pool (e.g., cognit-test-innovation-001)
3. Each user initializes its connection to the COGNIT platform with its device requirements
4. Users continuously execute tasks in a loop:
   - Wait a random time between MIN_WAIT and MAX_WAIT seconds
   - Execute the @task method (offload_stress_task)
   - Offload the stress_ng_cpu function to an edge node via COGNIT
   - The edge node runs stress-ng with the configured CPU load and duration
   - Wait again, then repeat
5. All execution metrics (latency, success/failure) are automatically logged to the database
6. The test runs until you stop it or the specified run-time expires
"""

import os
from common.cognit_device import CognitDevice
from locust import task, between


# ============================================================
# DEVICE POOL CONFIGURATION
# ============================================================
POOL_SIZE = 10  # Start small, scale up to 200 later


def stress_ng_cpu(duration: int, cpu_load: int, workers: int = 0):
    """
    Run stress-ng CPU workload with full parameter control.
    
    Args:
        duration: Stress duration (seconds)
        cpu_load: CPU load percentage (1-100) - passed to stress-ng --cpu-load
        workers: Number of CPU stressors (0 = use all available CPUs)
    
    Returns:
        Dict with execution results and metrics
    """
    import subprocess
    import time
    
    start = time.time()
    cmd = f"stress-ng --cpu {workers} --cpu-load {cpu_load} --timeout {duration}s"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    elapsed = time.time() - start
    
    return {
        "duration_requested": duration,
        "duration_actual": round(elapsed, 2),
        "cpu_load": cpu_load,
        "workers": workers,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr
    }


class EnergyCarbonEfficiencyScenario(CognitDevice):
    """
    Energy and carbon efficiency scenario with configurable stress-ng workload.
    
    This scenario uses a predefined pool of device IDs (configurable size, default 10).
    Each Locust user gets assigned exactly one unique device ID from the pool.
    Devices offload stress-ng CPU workloads with configurable parameters for
    measuring energy consumption and carbon emissions.
    
    IMPORTANT: The number of users must exactly match the pool size.
    Use: locust -f scenario_energy_carbon_efficiency.py --headless --users 10 --spawn-rate 1
    """
    
    # ============================================================
    # WORKLOAD CONFIGURATION - Full control over stress-ng
    # ============================================================
    CPU_LOAD = 50          # CPU load percentage (1-100) - passed to stress-ng --cpu-load
    CPU_WORKERS = 0        # Number of parallel CPU workers (0 = use all available CPUs)
    DURATION = 500           # Stress duration in seconds
    
    # ============================================================
    # FREQUENCY CONFIGURATION - Control request timing
    # ============================================================
    MIN_WAIT = 10          # Minimum seconds between requests
    MAX_WAIT = 20          # Maximum seconds between requests
    INITIAL_DELAY_MAX = 5  # Random delay at start to stagger requests
    
    # Pool-based scenarios automatically disable randomization
    randomize_device_id = False
    
    # Define fixed pool of device IDs
    device_id_pool = []
    for i in range(1, POOL_SIZE + 1):
        device_id_pool.append({
            "ID": f"cognit-test-innovation-{i:03d}",
            "FLAVOUR": "GlobalOptimizer",
            "PROVIDERS": ["ICE"],
            "GEOLOCATION": {
                "latitude": 42.2294,
                "longitude": 12.0687
            }
        })
    
    REQS_INIT = {
        "ID": "cognit-test-innovation-default",  # Will be overridden by pool assignment
        "FLAVOUR": "GlobalOptimizer",
        "PROVIDERS": ["ICE"],
        "GEOLOCATION": {
            "latitude": 42.2294,
            "longitude": 12.0687
        }
    }
    
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "cognit-config.yml")
    
    # wait_time references MIN_WAIT and MAX_WAIT class variables defined above
    # Python allows referencing class variables in class body if defined earlier
    wait_time = None  # Will be set after class definition
    
    @task
    def offload_stress_task(self):
        """Offload stress-ng workload with staggered timing."""
        # Add random initial delay on first run to stagger requests
        if not hasattr(self, '_first_run_done'):
            import random
            import time
            time.sleep(random.uniform(0, self.INITIAL_DELAY_MAX))
            self._first_run_done = True
        
        result = self.offload_function(
            stress_ng_cpu, 
            self.DURATION, 
            self.CPU_LOAD, 
            self.CPU_WORKERS
        )
        print("-----------------------------------------------")
        print(f"Device ID: {self.REQS_INIT['ID']}, CPU Load: {self.CPU_LOAD}%, Workers: {self.CPU_WORKERS}, Duration: {self.DURATION}s, Result: {result}")
        print("-----------------------------------------------")


# Set wait_time after class definition to reference class variables
EnergyCarbonEfficiencyScenario.wait_time = between(
    EnergyCarbonEfficiencyScenario.MIN_WAIT,
    EnergyCarbonEfficiencyScenario.MAX_WAIT
)

