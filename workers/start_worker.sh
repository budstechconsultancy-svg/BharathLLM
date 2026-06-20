#!/bin/bash
celery -A workers.celery_app worker --loglevel=info --concurrency=2
