# How to launch

REDIS_HOST=172.17.0.1 REDIS_PORT=6379 REDIS_PASSWORD=redis QUEUE=publish_worker,publish_worker_default ENV=production rake resque:work

Container must have platforms mounted in /platforms
