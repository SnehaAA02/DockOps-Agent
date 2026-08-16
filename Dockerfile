# Containerizes the agent process itself. To let it manage the HOST's
# Docker containers, mount the host's socket in at runtime:
#
#   docker run -it --rm \
#     -v /var/run/docker.sock:/var/run/docker.sock \
#     -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
#     dockops-agent
#
# SECURITY NOTE: mounting the Docker socket gives this container root-
# equivalent control over the host. Only do this on a trusted machine,
# never in a multi-tenant or production environment without a proxy like
# docker-socket-proxy in front of it.

FROM python:3.11-slim

# Docker CLI is required so the agent's tools can shell out to `docker ...`
# against the mounted socket.
RUN apt-get update && \
    apt-get install -y --no-install-recommends docker.io ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY dockops_agent ./dockops_agent

RUN pip install --no-cache-dir .

ENTRYPOINT ["dockops-agent"]
