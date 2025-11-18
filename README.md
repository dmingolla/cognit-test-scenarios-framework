# COGNIT Test Scenarios Framework

A reusable Locust-based load testing framework for COGNIT partners.

**Note:** This framework uses the `feature/release_prep` branch of device-runtime-py.

## Prerequisites

If you don't have the device-runtime-py repository, clone it first:

```bash
cd /opt
git clone -b feature/release_prep https://github.com/SovereignEdgeEU-COGNIT/device-runtime-py.git
```

Follow the installation instructions in the [device-runtime-py README](https://github.com/SovereignEdgeEU-COGNIT/device-runtime-py/tree/feature/release_prep) to build the COGNIT module.

## Installation

### Step 1: Create Virtual Environment

```bash
cd /opt/cognit-test-scenarios-framework
python3 -m venv .venv
source .venv/bin/activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Install COGNIT Module

Install the pre-built COGNIT module from device-runtime-py:

```bash
pip install /device-runtime-py/dist/cognit-0.0.0.tar.gz
```

**Note:** If the dist package doesn't exist, follow the build instructions in the device-runtime-py repository.

## Usage

Run the example scenario:

```bash
source .venv/bin/activate
locust -f test_cases/opennebula/scenario_light_load.py
```

Open `http://localhost:8089` in your browser to access the Locust web UI.

## How It Works

Locust spawns multiple "users" (devices) that run tasks concurrently. Each user is an instance of your scenario class, which inherits from `CognitDevice`. The `CognitDevice` base class handles:
- Device runtime initialization with COGNIT
- Function offloading to edge nodes
- Automatic metrics reporting to Locust

To create a new test case, simply inherit from `CognitDevice`, define your `REQS_INIT` configuration and `@task` methods. Each task calls `self.offload_function()` to execute workloads remotely. This abstraction means you only need to focus on defining your workload functions and device requirements, not the underlying COGNIT integration.

### CLI Examples

Run with specific number of devices and devices spawn rate:

```bash
# Run with 10 devices, spawn 2 devices per second
locust -f test_cases/opennebula/scenario_light_load.py --headless --users 10 --spawn-rate 2

# Run with 5 devices, spawn 1 devices per second, run for 60 seconds
locust -f test_cases/opennebula/scenario_light_load.py --headless --users 5 --spawn-rate 1 --run-time 60s

# Export metrics to CSV files (automatically generates stats, failures, and history CSVs)
locust -f test_cases/opennebula/scenario_light_load.py --headless --users 10 --spawn-rate 2 --csv=results/light_load_run1
```

## Device ID Management

The framework supports two approaches for device ID assignment:

### Randomized Device IDs (Default)

Scenarios without a device pool use randomized IDs. Each user gets a unique device ID generated from a base ID plus a UUID suffix. This is ideal for general load testing where device identity doesn't matter.

**Example scenarios:** `scenario_light_load.py`, `scenario_heavy_load.py`

```bash
# Works with any number of users
locust -f test_cases/opennebula/scenario_light_load.py --headless --users 10 --spawn-rate 2 --csv=results/light_load
```

### Fixed Device ID Pool

Scenarios with a `device_id_pool` use fixed device IDs for historical metrics tracking. Each user gets exactly one unique device ID from the pool, allowing you to track the same devices across multiple test runs.

**Key requirements:**
- The number of users **must exactly match** the pool size
- Each device ID is assigned exactly once (no duplicates)
- Pool is automatically reset after each test run

**Example scenario:** `scenario_device_pool.py` (50 device IDs)

```bash
# Correct: 50 users = 50 device IDs
locust -f test_cases/opennebula/scenario_device_pool.py --headless --users 50 --spawn-rate 5 --csv=results/pool_run1

# Error: User count doesn't match pool size
locust -f test_cases/opennebula/scenario_device_pool.py --headless --users 30 --spawn-rate 5
# Output: "ERROR: Device ID pool has 50 IDs but 30 users specified. They must match."
```

## Historical Metrics Tracking

To build a history of metrics over time:

1. **Use device pool scenarios** - Ensures the same device IDs are used across runs
2. **Export to CSV** - Use `--csv` flag to generate metrics files
3. **Run multiple times** - Execute the same scenario multiple times with different CSV output paths

**Example workflow:**

```bash
# Run 1
locust -f test_cases/opennebula/scenario_device_pool.py --headless --users 50 --spawn-rate 5 --csv=results/run_20240101

# Run 2 (same scenario, different timestamp)
locust -f test_cases/opennebula/scenario_device_pool.py --headless --users 50 --spawn-rate 5 --csv=results/run_20240102

# Run 3
locust -f test_cases/opennebula/scenario_device_pool.py --headless --users 50 --spawn-rate 5 --csv=results/run_20240103
```

**CSV files generated:**
- `*_stats.csv` - Request statistics (response times, request counts, failures)
- `*_failures.csv` - Failure details
- `*_stats_history.csv` - Time-series data showing metrics over time

You can then analyze these CSV files to track performance trends for each device ID across multiple test runs.
