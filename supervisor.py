#!/usr/bin/env python3
"""Starts one pvlogger.py worker per entry in the add-on option "loggers"."""

import json
import os
import signal
import subprocess
import sys
import threading
import time

OPTIONS_FILE = os.environ.get("PVLOGGER_OPTIONS", "/data/options.json")
WORKER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pvlogger.py")
RESTART_DELAY_SEC = 10

stopping = threading.Event()
processes = {}
lock = threading.Lock()


def log(message):
    print(message, flush=True)


def load_loggers():
    with open(OPTIONS_FILE) as f:
        loggers = json.load(f).get("loggers", [])
    result = []
    seen_ports = set()
    for index, entry in enumerate(loggers, start=1):
        name = (entry.get("name") or "").strip() or "logger%d" % index
        port = entry["serial_port"].strip()
        if port in seen_ports:
            log("[%s] Serial port %s is configured more than once, skipping" % (name, port))
            continue
        seen_ports.add(port)
        result.append({
            "name": name,
            "port": port,
            "system_id": str(entry["system_id"]).strip(),
            "api_key": entry["api_key"].strip(),
            "baudrate": str(entry.get("baudrate") or 9600),
        })
    return result


def run_worker(cfg):
    env = dict(os.environ,
               PVLOGGER_PORT=cfg["port"],
               PVLOGGER_SYSTEM_ID=cfg["system_id"],
               PVLOGGER_API_KEY=cfg["api_key"],
               PVLOGGER_BAUDRATE=cfg["baudrate"])
    prefix = "[%s] " % cfg["name"]
    while not stopping.is_set():
        proc = subprocess.Popen([sys.executable, "-u", WORKER], env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                universal_newlines=True)
        with lock:
            processes[cfg["name"]] = proc
        for line in proc.stdout:
            log(prefix + line.rstrip())
        proc.wait()
        if stopping.is_set():
            break
        log("%sWorker exited with code %s, restarting in %ds" % (prefix, proc.returncode, RESTART_DELAY_SEC))
        stopping.wait(RESTART_DELAY_SEC)


def shutdown(*_):
    stopping.set()
    with lock:
        for proc in processes.values():
            if proc.poll() is None:
                proc.terminate()


def main():
    loggers = load_loggers()
    if not loggers:
        log("No loggers configured. Add at least one entry under 'loggers' in the add-on configuration.")
        return 1

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    log("Starting %d logger(s): %s" % (len(loggers), ", ".join(c["name"] for c in loggers)))
    threads = [threading.Thread(target=run_worker, args=(cfg,), daemon=True) for cfg in loggers]
    for t in threads:
        t.start()
    while not stopping.is_set() and any(t.is_alive() for t in threads):
        time.sleep(1)
    for t in threads:
        t.join(timeout=5)
    return 0


if __name__ == "__main__":
    sys.exit(main())
