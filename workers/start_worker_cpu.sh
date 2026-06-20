#!/bin/bash
# Embedding worker — runs on CPU to avoid GPU memory conflict
CUDA_VISIBLE_DEVICES="" \
celery -A workers.celery_app worker \
  --loglevel=info \
  --concurrency=2 \
  --queues=embedding \
  -n worker_cpu@%h
