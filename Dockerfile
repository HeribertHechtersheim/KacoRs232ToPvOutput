FROM ghcr.io/home-assistant/base-python:3.14-alpine3.24

RUN python3 -m pip install --no-cache-dir pyserial==3.5

COPY pvlogger.py supervisor.py run.sh /app/
RUN chmod a+x /app/run.sh

CMD ["/app/run.sh"]
