from rq import Worker
import redis
import os

listen = ['default']

redis_conn = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
)

if __name__ == '__main__':
    # Keep finished/failed job results for 24 hours so the dashboard can display them.
    worker = Worker(listen, connection=redis_conn, default_result_ttl=86400)
    worker.work()

