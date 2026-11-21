# Kaco RS232 to PVOutput

A Home Assistant add-on that reads inverter measurements over a serial port
or a serial-to-network connection and uploads five-minute averages to
[PVOutput](https://pvoutput.org/). Multiple loggers can be configured.

The parser expects the ten-column format described in the
[add-on documentation](pvlogger/DOCS.md); compatibility with specific Kaco
models has not been verified.

## Installation

Add `https://github.com/HeribertHechtersheim/KacoRs232ToPvOutput` to the
repositories in the Home Assistant add-on store, then install the add-on.
