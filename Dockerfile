# Process Tree Explorer
#   docker build -t process-tree-explorer .
#   docker run --rm -p 8080:8080 process-tree-explorer
#   open http://localhost:8080  (the Live tab reads this container's /proc)
FROM python:3.12-slim

# tini becomes PID 1 so orphans get adopted and reaped, exactly what the app teaches.
# procps adds ps / pstree-style tools for poking around with `docker exec`.
RUN apt-get update \
 && apt-get install -y --no-install-recommends tini procps psmisc \
 && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 arya
WORKDIR /app
COPY server.py demo.py ./
COPY web/ ./web/
USER arya

ENV PORT=8080 PYTHONUNBUFFERED=1
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD python3 -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8080/api/processes')" || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python3", "server.py"]
