#!/usr/bin/env python3
"""Reads one inverter on a serial port and uploads 5-minute averages to PVOutput.

Configured through the environment: PVLOGGER_PORT, PVLOGGER_SYSTEM_ID,
PVLOGGER_API_KEY and optionally PVLOGGER_BAUDRATE.

Serial line format (10 whitespace separated columns):
  Date        Hour      Status Uin   Iin  Pin Uout  Iout Pout Temp
  04.06.2005  16:55:30  4      363.8 0.37 134 226.1 0.53 103  23
"""

import collections
import logging
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import serial

logger = logging.getLogger(__name__)

SERIAL_TIMEOUT_SEC = 15
INTERVAL_SEC = 60 * 5
MAX_REQUESTS_PER_INTERVAL = 5
UPLOAD_QUEUE_LEN = 1000
MIN_ENTRIES_FOR_AVG = 3
HTTP_TIMEOUT_SEC = 15
ADD_STATUS_URL = "https://pvoutput.org/service/r2/addstatus.jsp"


class ApiError(Exception):
    pass


def upload(api_key, system_id, data):
    local_time = time.localtime(data["timeStamp"])
    fields = [
        ("d", time.strftime("%Y%m%d", local_time)),
        ("t", time.strftime("%H:%M", local_time)),
        ("v2", str(int(round(data["pOut"])))),
        ("v4", str(int(round(data["pIn"])))),
        ("v5", str(round(data["temp"], 1))),
        ("v6", str(round(data["uIn"], 1))),
    ]
    request = urllib.request.Request(
        ADD_STATUS_URL,
        data=urllib.parse.urlencode(fields).encode(),
        headers={"X-Pvoutput-Apikey": api_key, "X-Pvoutput-SystemId": system_id},
    )
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SEC) as response:
            message = response.read().decode(errors="replace").strip()
    except urllib.error.HTTPError as error:
        message = error.read().decode(errors="replace").strip()
        raise ApiError("Upload failed, HTTP %d: %s" % (error.code, message))
    if message != "OK 200: Added Status":
        raise ApiError("Upload not successful, message: " + message)


def init_port(port, path, baudrate):
    try:
        port.close()
        port.baudrate = baudrate
        port.timeout = SERIAL_TIMEOUT_SEC
        port.open()
    except Exception as error:
        print("Unable to init serial port %s: %s" % (path, error))
        time.sleep(5)


def read_input(port):
    """Returns a parsed record, None for an unparsable line, raises TimeoutError on silence."""
    while True:
        raw = port.readline()
        if raw == b"":
            raise TimeoutError("No data received from " + str(port.port))
        line = raw.decode(errors="replace").strip()
        if line:
            break

    cols = line.split()
    if len(cols) != 10:
        return None
    try:
        return {
            "uIn": float(cols[3]),
            "iIn": float(cols[4]),
            "pIn": int(cols[5]),
            "uOut": float(cols[6]),
            "iOut": float(cols[7]),
            "pOut": int(cols[8]),
            "temp": int(cols[9]),
        }
    except ValueError as error:
        print("Invalid line %r: %s" % (line, error))
        return None


def main():
    path = os.environ["PVLOGGER_PORT"]
    system_id = os.environ["PVLOGGER_SYSTEM_ID"]
    api_key = os.environ["PVLOGGER_API_KEY"]
    baudrate = int(os.environ.get("PVLOGGER_BAUDRATE", "9600"))

    port = serial.serial_for_url(path, do_not_open=True)
    queue = collections.deque(maxlen=UPLOAD_QUEUE_LEN)
    init_port(port, path, baudrate)
    print("Logging %s to PVOutput system %s" % (path, system_id))

    while True:
        n = 0
        requests = 0
        sums = {}
        interval_end = (time.time() // INTERVAL_SEC + 1) * INTERVAL_SEC

        while time.time() < interval_end:
            try:
                data = read_input(port)
            except Exception as error:
                print(error)
                init_port(port, path, baudrate)
                continue
            if data is None:
                continue
            n += 1
            for key, value in data.items():
                sums[key] = sums.get(key, 0) + value

        if n >= MIN_ENTRIES_FOR_AVG:
            avg = {key: value / n for key, value in sums.items()}
            logger.debug(time.strftime("%d.%m.%Y %H:%M", time.localtime(interval_end)) + ", n=%d: %s" % (n, avg))
            avg["timeStamp"] = interval_end
            queue.append(avg)

        while queue and requests < MAX_REQUESTS_PER_INTERVAL:
            try:
                upload(api_key, system_id, queue[0])
            except Exception as error:
                print(error)
                time.sleep(5)
            else:
                queue.popleft()
            finally:
                requests += 1

        if queue:
            print("Queued data length: %d" % len(queue))


if __name__ == "__main__":
    sys.exit(main())
