# PV Logger RS232 to PVOutput

Reads solar inverter data from serial (RS232 / USB-serial) ports and uploads
5-minute averages to [PVOutput.org](https://pvoutput.org). Any number of
inverters can be configured; each one runs as its own worker process.

## Configuration

```yaml
loggers:
  - name: roof_south        # optional, used as log prefix
    serial_port: /dev/ttyUSB0
    system_id: "12345"
    api_key: your-pvoutput-api-key
    baudrate: 9600          # optional, default 9600
  - name: roof_north
    serial_port: /dev/ttyUSB1
    system_id: "12346"
    api_key: your-pvoutput-api-key
```

`serial_port` can also be a network URL, e.g. for a serial-to-Ethernet
converter or `ser2net`: `socket://192.168.1.50:4001` (raw TCP) or
`rfc2217://192.168.1.50:4001` (RFC 2217). Dropped connections are reopened
automatically.

Each serial port may only be used once. Use stable device paths such as
`/dev/serial/by-id/...` if the `ttyUSB` numbering changes between reboots.
Failing workers are restarted automatically.
