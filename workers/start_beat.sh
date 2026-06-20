#!/bin/bash
celery -A workers.celery_app beat --loglevel=info
