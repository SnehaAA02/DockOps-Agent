# DockOps Agent

![CI](https://github.com/SnehaAA02/dockops-agent/actions/workflows/ci.yml/badge.svg)

A local, LLM-powered assistant for inspecting and managing Docker containers
through natural language, built on LangChain and a locally-hosted Ollama
model (no data leaves your machine).

```
"show me what's running and check the logs on the api container"
        │
        ▼
 ┌─────────────┐    tool calls    ┌────────────────────┐
 │ LangChain    │ ───────────────▶│ Docker CLI wrappers │──▶ docker ps / logs / stats
 │ Agent (Qwen) │◀─────────────── │ (validated, no      │
 └─────────────┘   tool results   │  shell=True)        │
                                   └────────────────────┘
```
## Use-Cases 

- Onboarding / low Docker-fluency teammates
Junior engineers or non-backend folks (QA, support, PMs poking at a staging environment) who need to check container status but don't know Docker syntax by heart yet.
- Fast triage during an incident, on a dev/staging box
Someone mid-incident, tired, under pressure — typing a fast plain-English question is lower friction than recalling exact flag syntax at 2am.
- Personal dev-environment hygiene
An individual developer's own machine — checking what's eating resources, cleaning up forgotten containers, before starting a fresh dev session.
- Shared dev-server cleanup helper (needs more guardrails)
A team's shared dev/test server accumulates orphaned containers over time — an internal tool anyone on the team can point at it periodically.


## Features

- **Six Docker tools**: list containers (running/all), tail logs, start,
  stop, live resource stats, and list images
- **Safe by construction**: every subprocess call uses list-form args (no
  shell injection surface) and validates container/image identifiers before
  they're used, even though the LLM is the one supplying them
- **Never crashes on tool failure**: Docker-not-installed, timeouts, and
  CLI errors are all caught and turned into readable messages the agent can
  reason about
- **Two run modes**: one-shot (`--query`) for scripting/CI, or an
  interactive REPL for exploratory use
- **Config via environment variables**, not hardcoded paths — runs the same
  on any machine or in a container
- **Unit tested**: `subprocess` is mocked so the test suite runs without
  Docker or Ollama installed

## Project layout

```
dockops-agent/
├── dockops_agent/
│   ├── agent.py            # CLI entrypoint, REPL, agent wiring
│   ├── config.py           # env-driven settings
│   └── tools/
│       └── docker_tools.py # the 6 tools exposed to the LLM
├── tests/
│   └── test_docker_tools.py
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

```bash
git clone https://github.com/YOUR_USERNAME/dockops-agent.git
cd dockops-agent

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"          # installs the package + the `dockops-agent` CLI + test/lint tools

# Pull the model once (requires Ollama installed and running: https://ollama.com)
ollama pull qwen2.5

cp .env.example .env             # adjust if needed
```

Requires Docker Desktop (or the Docker daemon) running locally so the
agent's tools have something real to talk to.

## Usage

```bash
# Interactive
dockops-agent

# One-shot (handy for scripts/CI)
dockops-agent -q "list all containers, including stopped ones"

# Equivalent, without installing the console script
python -m dockops_agent.agent -q "show me container stats"
```

## Testing

Tests are **real integration tests against a live Docker daemon** — no
mocks. They pull `alpine:latest`, spin up a disposable container, exercise
every tool (list/logs/stop/start/stats/images) against it, and tear it down
afterward. If Docker isn't available on your machine, the suite skips
cleanly rather than failing.

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

Runs automatically on every push via GitHub Actions (`.github/workflows/ci.yml`),
on `ubuntu-latest` runners which have Docker preinstalled — so CI is
exercising real containers too, not a mocked stand-in.

## Running the agent itself in Docker

```bash
docker build -t dockops-agent .
docker run -it --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  dockops-agent
```

This mounts the host's Docker socket so the containerized agent can manage
containers on the host. See the security note in the `Dockerfile` — this
grants root-equivalent access to the host and should only be done on a
trusted machine.

## CI/CD pipeline

.github/workflows/ci.yml runs two jobs on every push to main/master:

- test — lints with ruff, then runs the real Docker integration suite on a fresh runner (see Testing above).
- publish — only runs if test passes, and only for actual pushes (never for pull requests, so a PR can't publish an image under your name). Builds the Docker image and pushes it to GitHub Container Registry, tagged both latest and with the short git commit SHA for traceability.

## Design decisions worth knowing for a walkthrough

- **Why list-form subprocess args over `shell=True`**: the LLM ultimately
  decides what string gets passed as a container name — treating that as
  untrusted input and validating it against Docker's own naming rules is
  the same discipline you'd apply to any user-facing input field.
- **Why tools return strings, never raise**: LangChain agents can only
  reason over text. An uncaught exception kills the whole run; a returned
  error string lets the model explain the failure to the user and, in a
  future version, retry or suggest a fix.
- **Why config is env-driven**: the original script had a hardcoded Windows
  path check baked into the entrypoint, which meant it literally would not
  run on another OS or another engineer's machine. Settings now come from
  environment variables with defaults, which is what lets this run
  unmodified in a Docker image, CI runner, or teammate's laptop.


## Possible extensions

- Swap `ChatOllama` for a hosted model behind a feature flag
- Add `docker_inspect` / `docker_exec` more tools with tighter allow-lists
- Stream agent responses token-by-token in the REPL
- Wrap in a small FastAPI service for a Slack/Teams bot front end
- Adding remote Docker context support (Docker's own DOCKER_HOST / contexts feature lets you point the CLI at a remote daemon over SSH)

---

