# NAT Collector Service Installation

## Option 1: NSSM (Recommended)

### Download NSSM
1. Download NSSM from: https://nssm.cc/download
2. Extract to a folder (e.g., `C:\nssm\`)
3. Add to PATH or use full path to nssm.exe

### Install Collector Service

Open PowerShell or Command Prompt **as Administrator** and run:

```cmd
cd D:\GitHub\vatsim-nat

# Install collector service
C:\nssm\nssm.exe install NATCollector "C:\Program Files\WindowsApps\PythonSoftwareFoundation.Python.3.12_3.12.2800.0_x64__qbz5n2kfra8p0\python.exe" "D:\GitHub\vatsim-nat\collector_service.py"

# Set working directory
C:\nssm\nssm.exe set NATCollector AppDirectory "D:\GitHub\vatsim-nat"

# Set description
C:\nssm\nssm.exe set NATCollector Description "VATSIM NAT Traffic Collector"

# Configure auto-restart on failure
C:\nssm\nssm.exe set NATCollector AppRestartDelay 30000

# Set to start automatically
C:\nssm\nssm.exe set NATCollector Start SERVICE_AUTO_START

# Start the service
C:\nssm\nssm.exe start NATCollector
```

### Service Management

```cmd
# Check status
C:\nssm\nssm.exe status NATCollector

# Stop service
C:\nssm\nssm.exe stop NATCollector

# Restart service
C:\nssm\nssm.exe restart NATCollector

# Remove service (if needed)
C:\nssm\nssm.exe remove NATCollector confirm
```

## Option 2: Task Scheduler (Already Configured)

If you prefer to keep using Task Scheduler, you can update the existing task or create a new one:

### Create New Task
1. Open Task Scheduler (taskschd.msc)
2. Create Basic Task
3. Name: "NAT Collector"
4. Trigger: "When the computer starts"
5. Action: "Start a program"
6. Program: `C:\Program Files\WindowsApps\PythonSoftwareFoundation.Python.3.12_3.12.2800.0_x64__qbz5n2kfra8p0\python.exe`
7. Arguments: `collector_service.py`
8. Start in: `D:\GitHub\vatsim-nat`
9. Run whether user is logged on or not
10. Run with highest privileges

## Current Status

Currently the collector is running manually in the background (PID from process list).
After setting up the service, kill the manual process:

```cmd
# Find Python processes
tasklist | findstr python

# Kill specific PID
taskkill /PID <pid> /F
```

## Verification

After starting the service, check:
- Service is running: `sc query NATCollector` or Task Scheduler
- Log file is being updated: `tail -f D:\GitHub\vatsim-nat\nat_collector.log`
- Database is being updated: Check last_update_time in nat_traffic.db
