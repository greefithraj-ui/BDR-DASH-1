
import time
import subprocess
import sys
from pathlib import Path
import urllib.request
import json

# Configuration
HEALTH_URL = "http://localhost:8000/api/health"
CHECK_INTERVAL = 30  # Check every 30 seconds
MAX_STALE_TIME = 300  # 5 minutes
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUN_PY = PROJECT_ROOT / "run.py"


def check_health():
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=10) as response:
            data = json.loads(response.read().decode())
            if data.get("status") == "healthy":
                return True
            # Check last successful sync
            last_sync = data.get("last_successful_sync")
            if last_sync is not None and (time.time() - last_sync) < MAX_STALE_TIME:
                return True
            return False
    except Exception as e:
        print(f"Health check failed: {e}")
        return False


def restart_service():
    print("Restarting service...")
    # First, try to stop via run.py
    try:
        # This is just an example, adjust based on your needs
        # For now, we'll just log that restart is needed
        print("Manual restart required or implement proper restart logic")
    except Exception as e:
        print(f"Error restarting service: {e}")


def main():
    print("Watchdog started. Monitoring health...")
    while True:
        healthy = check_health()
        if not healthy:
            print("Service is not healthy!")
            restart_service()
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
