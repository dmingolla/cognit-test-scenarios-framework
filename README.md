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
```

## Device ID Management

The framework supports two approaches for device ID assignment:

### Randomized Device IDs (Default)

Scenarios without a device pool use randomized IDs. Each user gets a unique device ID generated from a base ID plus a UUID suffix. This is ideal for general load testing where device identity doesn't matter.

**Example scenarios:** `scenario_light_load.py`, `scenario_heavy_load.py`

```bash
# Works with any number of users
locust -f test_cases/opennebula/scenario_light_load.py --headless --users 10 --spawn-rate 2
```

### Fixed Device ID Pool

Scenarios with a `device_id_pool` use fixed device IDs for historical metrics tracking. Each user gets exactly one unique device ID from the pool, allowing you to track the same devices across multiple test runs.

**Key requirements:**
- The number of users **must exactly match** the pool size
- Each device ID is assigned exactly once (no duplicates)
- Pool is automatically reset after each test run

**Example scenario:** `scenario_device_pool.py` (10 device IDs)

```bash
# Correct: 10 users = 10 device IDs
locust -f test_cases/opennebula/scenario_device_pool.py --headless --users 10 --spawn-rate 2

# Error: User count doesn't match pool size
locust -f test_cases/opennebula/scenario_device_pool.py --headless --users 5 --spawn-rate 2
# Output: "ERROR: Device ID pool has 10 IDs but 5 users specified. They must match."
```

## Metrics Database

All test execution results are automatically stored in a local SQLite database (`results/metrics.db`). Each time a task completes (success or failure), a record is created with detailed information about that execution.

### What's Stored

The database tracks:
- **Execution metadata**: Run ID (shared across all devices in a test run), timestamp, scenario name
- **Device information**: Device ID, device requirements (flavor, geolocation, etc.)
- **Task details**: Task name, request parameters
- **Performance metrics**: Latency (execution time), status (SUCCESS/FAILURE), error messages

### Analyzing Results

The `scripts/` directory contains example analysis scripts. You can use these as templates to build your own custom analysis:

```bash
# Run the example pandas analysis script
python3 scripts/analyze_pandas.py
```

This script demonstrates how to:
- Load data from the SQLite database
- Group metrics by run ID and scenario name
- Calculate aggregate statistics (average latency, success rates, device counts)

### Types of Analysis You Can Perform

With the stored data, you can perform various analyses:

- **Performance Trends**: Compare average latency across different test runs (e.g., yesterday vs. today)
- **Device-Level Tracking**: Track performance of specific devices over time (especially useful with device pool scenarios)
- **Failure Analysis**: Identify patterns in failures by device, scenario, or time period
- **Scenario Comparison**: Compare performance metrics between different scenarios
- **Historical Regression**: Detect performance degradation by comparing metrics from the same scenario across multiple runs

The database structure allows you to filter, group, and aggregate data by any combination of dimensions (scenario, device ID, timestamp, run ID) to answer specific questions about your test results.
