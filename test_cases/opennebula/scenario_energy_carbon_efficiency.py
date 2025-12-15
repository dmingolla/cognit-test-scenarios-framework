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
5. The test runs until you stop it or the specified run-time expires


!!! IMPORTANT: The number of users you pass in the command line below, must exactly match the value of the POOL_SIZE variable.

Use: locust -f scenario_energy_carbon_efficiency.py --headless --users <POOL_SIZE> --spawn-rate <SPAWN_RATE> --run-time <RUN_TIME>
"""

import os
from common.cognit_device import CognitDevice
from locust import task, between
from common.logger import logger


# ============================================================
# CONFIGURATION
# ============================================================

# DEVICE POOL CONFIGURATION
POOL_SIZE = 5  # Number of devices to simulate

# WORKLOAD CONFIGURATION
# Option 1: Same load for all devices - Set USE_PER_DEVICE_LOAD = False
# Option 2: Different load per device - Set USE_PER_DEVICE_LOAD = True and configure in device_id_pool below
USE_PER_DEVICE_LOAD = False  # If True, each device uses its own CPU_LOAD from device_id_pool
CPU_LOAD = 50          # Default CPU load % (1-100) - used when USE_PER_DEVICE_LOAD = False
CPU_WORKERS = 0        # Number of CPU workers (0 = use all available CPUs)
DURATION = 500         # Stress duration per request in seconds

# REQUEST TIMING CONFIGURATION (staggering to avoid simultaneous requests)
MIN_WAIT = 10          # Minimum seconds between requests (random wait range)
MAX_WAIT = 20          # Maximum seconds between requests (random wait range)
INITIAL_DELAY_MAX = 5  # Random delay at start (0 to this value) to stagger device initialization

# Validate configuration
if MIN_WAIT > MAX_WAIT:
    raise ValueError(f"MIN_WAIT ({MIN_WAIT}) must be <= MAX_WAIT ({MAX_WAIT})")
if DURATION <= 0:
    raise ValueError(f"DURATION ({DURATION}) must be > 0")
if CPU_WORKERS < 0:
    raise ValueError(f"CPU_WORKERS ({CPU_WORKERS}) must be >= 0")


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
    
    # Validate inputs
    cpu_load = int(max(0, min(100, cpu_load)))
    duration = max(1, int(duration))  # At least 1 second
    workers = max(0, int(workers))
    
    start = time.time()
    cmd = f"stress-ng --cpu {workers} --cpu-load {cpu_load} --timeout {duration}s"
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=duration + 10)
    except subprocess.TimeoutExpired:
        return {
            "duration_requested": duration,
            "duration_actual": round(time.time() - start, 2),
            "cpu_load": cpu_load,
            "workers": workers,
            "returncode": -1,
            "stdout": "",
            "stderr": "stress-ng command timed out",
            "error": "Command execution timeout"
        }
    except Exception as e:
        return {
            "duration_requested": duration,
            "duration_actual": round(time.time() - start, 2),
            "cpu_load": cpu_load,
            "workers": workers,
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
            "error": "Command execution failed"
        }
    
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
    
    This scenario uses a predefined pool of device IDs (configurable size).
    Each Locust user gets assigned exactly one unique device ID from the pool.
    Devices offload stress-ng CPU workloads with configurable parameters for
    measuring energy consumption and carbon emissions.
    """
    
    # Pool-based scenarios automatically disable randomization
    randomize_device_id = False
    
    # Define fixed pool of device IDs
    # If USE_PER_DEVICE_LOAD = True, you can add "CPU_LOAD" to each device dict below
    device_id_pool = []
    for i in range(1, POOL_SIZE + 1):
        device_config = {
            "ID": f"cognit-test-innovation-{i:03d}",
            "FLAVOUR": "GlobalOptimizer",
            "PROVIDERS": ["ICE"],
            "GEOLOCATION": {
                "latitude": 42.2294,
                "longitude": 12.0687
            }
        }
        
        # Add per-device CPU load if enabled
        if USE_PER_DEVICE_LOAD:
            # Linear progression (Device 1=10%, Device 2=20%, Device 3=30%, etc.)

            device_config["CPU_LOAD"] = min(100, max(0, int(10 * i)))
            
            # Specific values for each device (define list outside loop, then use index)
            # pre_defined_cpu_loads = [25, 50, 75, 100, 30, 60, 90, 40, 70, 80]
            # if len(pre_defined_cpu_loads) < POOL_SIZE:
            #     raise ValueError(f"pre_defined_cpu_loads must have at least {POOL_SIZE} elements")
            # device_config["CPU_LOAD"] = pre_defined_cpu_loads[i-1]
            
            # Random distribution (each device gets different random value)
            # device_config["CPU_LOAD"] = random.randint(20, 80)
        
        device_id_pool.append(device_config)
    
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
            time.sleep(random.uniform(0, INITIAL_DELAY_MAX))
            self._first_run_done = True
        
        # Use per-device CPU load if configured, otherwise use default
        cpu_load = self.REQS_INIT.get("CPU_LOAD", CPU_LOAD)
        
        # Validate CPU load is integer between 0-100
        cpu_load = int(max(0, min(100, cpu_load)))
        
        logger.info(f"Offloading stress-ng CPU workload for device {self.REQS_INIT['ID']} with CPU load {cpu_load}%, workers {CPU_WORKERS}, duration {DURATION}s")
        result = self.offload_function(
            stress_ng_cpu, 
            DURATION, 
            cpu_load, 
            CPU_WORKERS
        )


# Set wait_time after class definition to reference configuration variables
EnergyCarbonEfficiencyScenario.wait_time = between(MIN_WAIT, MAX_WAIT)

