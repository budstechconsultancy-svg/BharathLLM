#!/bin/bash
# GPU worker — for tasks that need CUDA (future use)
celery -A workers.celery_app worker \
  --loglevel=info \
  --concurrency=1 \
  --queues=gpu \
  -n worker_gpu@%h
