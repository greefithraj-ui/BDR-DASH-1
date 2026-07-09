import glob
import sys
import os
os.environ["PYTHONUNBUFFERED"] = "1"
sys.path.insert(0, os.path.dirname(__file__))
import run
import time
import subprocess

ROOT = os.path.dirname(__file__)
LOG_FILE = os.path.join(ROOT, "data", "api_bg.log")
FRONTEND_TIMEOUT = 60
API_TIMEOUT = 90


def _creationflags():
    if os.name == "nt":
        return subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    return 0


def _tail_log(filepath, n=10):
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        tail = [l.rstrip() for l in lines[-n:]]
        for l in tail:
            fatal = any(kw in l.lower() for kw in ("error", "traceback", "fatal", "exception"))
            prefix = "[!] " if fatal else "    "
            print(f"       {prefix}{l}")
    except Exception:
        pass


print("Starting PostgreSQL...")
pg_ok = run._pg_ensure()
if pg_ok:
    print("PostgreSQL ready!")
else:
    print("PostgreSQL not available, will use file fallback.")

print("Starting API server...")
run._kill_port(8000)
for _f in glob.glob(os.path.join(ROOT, "data", "*.pid")):
    try:
        os.remove(_f)
    except OSError:
        pass
run._kill_port(3001)

log_handle = open(LOG_FILE, "w", encoding="utf-8")
env = os.environ.copy()
env["AQC_PASSWORD"] = env.get("AQC_PASSWORD", "1234")
api_proc = subprocess.Popen(
    [sys.executable, os.path.join(ROOT, "data", "main.py"), "--bg-api"],
    cwd=ROOT,
    stdout=log_handle,
    stderr=subprocess.STDOUT,
    env=env,
    creationflags=_creationflags(),
)

print("Starting frontend (static server)...")
frontend_proc = subprocess.Popen(
    ["node", "serve-dist.js"],
    cwd=ROOT,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    creationflags=_creationflags(),
)


def _wait_with_process_check(port, proc, timeout, label, log_file=None):
    start = time.time()
    while time.time() - start < timeout:
        if proc.poll() is not None:
            elapsed = int(time.time() - start)
            print(f"       [!!] {label} process exited unexpectedly after {elapsed}s (code: {proc.returncode})")
            if log_file:
                print(f"       [..] Last log lines:")
                _tail_log(log_file, 15)
            return None
        pid = run._find_pid_by_port(port)
        if pid:
            return pid
        elapsed = int(time.time() - start)
        if elapsed > 0 and elapsed % 5 == 0:
            print(f"       [~] Waiting for {label}... {elapsed}s")
        time.sleep(0.5)
    elapsed = int(time.time() - start)
    print(f"       [!!] {label} did not start within {elapsed}s")
    if log_file:
        if proc.poll() is None:
            print(f"       [..] Process still running, dumping recent log:")
        else:
            print(f"       [..] Process died (code: {proc.returncode}), dumping log:")
        _tail_log(log_file, 15)
    return None


print("Waiting for API (port 8000)...")
api_pid = _wait_with_process_check(8000, api_proc, API_TIMEOUT, "API", LOG_FILE)

print("Waiting for frontend (port 3001)...")
frontend_pid = _wait_with_process_check(3001, frontend_proc, FRONTEND_TIMEOUT, "Frontend")

log_handle.close()

run._write_pids({"api": api_pid, "vite": frontend_pid})

if api_pid and frontend_pid:
    print("=" * 70)
    print(f"API running: http://localhost:{8000} (PID {api_pid})")
    print(f"Frontend running: http://localhost:{3001} (PID {frontend_pid})")
    print("=" * 70)
    print("All services started!")
elif api_pid:
    print("[!!] Frontend failed to start, but API is running.")
    print(f"API: http://localhost:{8000} (PID {api_pid})")
elif frontend_pid:
    print("[!!] API failed to start, but Frontend is running.")
    print(f"Frontend: http://localhost:{3001} (PID {frontend_pid})")
else:
    print("[!!] Both services failed to start.")
    print("Check logs above for details. Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting.")

try:
    while True:
        if api_proc.poll() is not None and frontend_proc.poll() is not None:
            print("Both processes have exited. Shutting down.")
            break
        if api_proc.poll() is not None:
            print("API process exited unexpectedly, stopping all services.")
            run._stop()
            frontend_proc.terminate()
            break
        if frontend_proc.poll() is not None:
            print("Frontend process exited unexpectedly, stopping all services.")
            run._stop()
            api_proc.terminate()
            break
        time.sleep(1)
except KeyboardInterrupt:
    print("\nShutting down...")
    run._stop()
    api_proc.terminate()
    frontend_proc.terminate()
    try:
        api_proc.wait(timeout=5)
    except Exception:
        api_proc.kill()
    try:
        frontend_proc.wait(timeout=5)
    except Exception:
        frontend_proc.kill()
    print("Shutdown complete!")
