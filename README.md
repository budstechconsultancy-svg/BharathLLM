# BharatLLM Government Multi-Department Document Intelligence System

A Python + Node.js monorepo containing a multi-department Document Intelligence System powered by LLaMA 3.1 8B (QLoRA), BGE-M3 embeddings, Qdrant, PostgreSQL, and React.

## Directory Structure
- `/data/raw` - original PDF storage
- `/data/processed` - OCR-extracted raw text
- `/data/cleaned` - cleaned and normalised text
- `/data/chunks` - chunked documents for RAG
- `/data/training` - Alpaca-format fine-tuning dataset
- `/data/embeddings` - local embedding cache
- `/pipeline` - processing pipeline scripts
- `/api` - FastAPI gateway
- `/auth` - JWT authentication service
- `/workers` - Celery task queue workers
- `/models` - fine-tuned model checkpoints
- `/evaluation` - benchmarking scripts and eval dataset
- `/logs` - system and process logs
- `/frontend` - React portals (chat, admin, api-dev)
- `/deploy` - deployment configurations

## Set up
1. Install Python dependencies: `poetry install`
2. Install frontend dependencies: `cd frontend && npm install`
3. Configure environment: Copy `.env.example` to `.env` and fill out variables.
