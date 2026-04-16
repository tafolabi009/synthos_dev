# SynthOS

AI training data validation platform. Detects model collapse before it reaches production.

## What it does

SynthOS validates synthetic and curated training datasets by running cascade validation across 15+ proxy models (1M–500M parameters). It predicts model collapse with 90%+ accuracy before you commit to a full training run.

## Core Features

- **Cascade Validation** — trains progressively larger proxy models to detect data quality degradation at each scale
- **Collapse Prediction** — spectral analysis identifies collapse signatures before they manifest in full-scale training
- **Quality Scoring** — automated data quality metrics with statistical distribution analysis
- **Differential Privacy** — OpenDP integration for privacy-preserving validation
- **Multi-format Support** — CSV, JSON, Parquet, Excel with AI-powered schema detection
- **Real-time Monitoring** — live progress tracking and quality dashboards

## Stack

- Python, PyTorch
- Claude/Anthropic API for schema detection
- Stripe + Paddle billing integration
- Docker, Docker Compose

## Quick Start

```bash
git clone https://github.com/tafolabi009/synthos-dev.git
cd synthos-dev
cp .env.example .env
docker-compose up -d
```

## Status

Alpha — core validation engine functional, enterprise features in development.

## Links

- [synthos.dev](https://synthos.dev)
- [ML Backend](https://github.com/tafolabi009/synthos-ml-backend)
