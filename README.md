# Intraclass Correlation ICC Calc

> **Domain:** Clinical Decision Support & Biomedical Computing

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## Overview

Intraclass Correlation Coefficient (ICC) calculator with multi-agent evaluation pipeline. Provides single and batch evaluation modes, a FastAPI REST API, and a CLI with audit trail capabilities.

Author: Dr. Abu Suraih Sakhri
License: MIT

---

## Features

- **Single Evaluation**: Process individual cases via CLI
- **Batch Processing**: Process CSV files with multiple records
- **Multi-Agent Pipeline**: InvariantQC, Safety Escalation, and Protocol Conformance workers
- **PHI Guard**: Zero-PHI outbound interceptor blocking SSNs, MRNs, phone numbers, and patient identifiers
- **HMAC-SHA256 Audit Trail**: Tamper-evident cryptographic logging
- **FastAPI REST API**: OpenAPI-compatible endpoints with health and metrics
- **Prometheus Metrics**: Operational telemetry exporter

---

## Installation

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/intraclass-correlation-icc-calc.git
cd intraclass-correlation-icc-calc

# Install dependencies
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```

---

## Usage

### CLI Commands

#### Single Evaluation
```bash
python cli.py single --v1 12.0 --v2 4.0 --v3 2.0
```

#### Batch Processing
```bash
python cli.py batch -i sample.csv -o results.csv
```

#### Audit Mode (Multi-Agent)
```bash
python cli.py audit --task-id TASK-001 --primary 28.5 --secondary 14.2
```

#### Chat Query
```bash
python cli.py chat "Explain specifications"
```

#### Verify Audit Trail
```bash
python cli.py verify-audit
```

#### Start API Server
```bash
python cli.py serve --host 127.0.0.1 --port 8000
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/metrics` | GET | System metrics |
| `/api/audit` | POST | Submit task for evaluation |
| `/api/chat` | POST | Query supervisory chat |
| `/api/audit/logs` | GET | Get audit trail |

---

## Input Data Schema (Batch CSV)

| Field | Description | Requirement |
|:------|:------------|:------------|
| `Patient_ID` | Patient identifier | Required |
| `v1` | Primary measurement | Required |
| `v2` | Secondary measurement | Required |
| `v3` | Tertiary measurement | Required |

---

## Security

- **Zero-PHI Outbound Interceptor**: AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers
- **HMAC-SHA256 Audit Trail**: Chained, cryptographically signed logs
- **Input Validation**: Path traversal protection on file operations
- **Secure Defaults**: Auto-generated cryptographic secrets when not configured via environment variable

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AUDIT_SECRET_KEY` | HMAC secret key for audit trail | Auto-generated (random) |
| `MODEL_PROVIDER` | LLM provider (mock, ollama, claude, openai) | mock |

---

## Testing

```bash
# Run all tests
pytest -v

# Run with coverage
pytest -v --cov

# Run simulation benchmark
python simulator.py 1000
```

---

## Docker Deployment

```bash
# Build and run with Docker Compose
export AUDIT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
docker-compose up --build

# Or with Docker directly
docker build -t intraclass-correlation-icc-calc .
docker run -p 8000:8000 -e AUDIT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))") intraclass-correlation-icc-calc
```

---

## Project Structure

```
intraclass-correlation-icc-calc/
├── agents/              # Multi-agent evaluation pipeline
│   ├── base.py          # PHI Guard, Audit Trail, Security
│   ├── models.py        # Pydantic data models
│   ├── workers.py       # Specialized evaluation workers
│   ├── supervisor.py    # Orchestrator
│   ├── api.py           # FastAPI endpoints
│   ├── metrics.py       # Prometheus metrics
│   ├── llm_factory.py   # LLM provider factory
│   ├── learning.py      # Bayesian calibration engine
│   └── streamer.py      # WebSocket telemetry
├── tests/               # Test suite
├── web/                 # Web console (HTML)
├── cli.py               # CLI entry point
├── icc_calc.py          # Core calculation functions
├── enrichment.py        # Enrichment feature engines
├── simulator.py         # Load testing simulator
├── pyproject.toml       # Project configuration
├── Dockerfile           # Container build
└── docker-compose.yml   # Container orchestration
```
