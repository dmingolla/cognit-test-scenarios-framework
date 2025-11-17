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
