import os
import json
import logging
import redis

# Setup Redis connection client
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r_client = redis.from_url(REDIS_URL)

def store_job(job_id: str, data: dict):
    # Store task metadata fields inside Redis hashes
    key = f"job:{job_id}"
    serialized_data = {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) for k, v in data.items()}
    r_client.hset(key, mapping=serialized_data)
    r_client.expire(key, 86400) # TTL: 24 Hours

def get_job(job_id: str) -> dict:
    key = f"job:{job_id}"
    data = r_client.hgetall(key)
    if not data:
        return {}
        
    decoded_data = {}
    for k, v in data.items():
        k_str = k.decode("utf-8")
        v_str = v.decode("utf-8")
        try:
            decoded_data[k_str] = json.loads(v_str)
        except Exception:
            decoded_data[k_str] = v_str
            
    return decoded_data

def list_jobs(department: str = None) -> list:
    keys = r_client.keys("job:*")
    jobs = []
    for key in keys:
        job_id = key.decode("utf-8").split(":")[1]
        job = get_job(job_id)
        if job:
            if department and job.get("department") != department:
                continue
            jobs.append(job)
    return jobs
