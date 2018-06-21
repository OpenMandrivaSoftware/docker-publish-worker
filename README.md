# How to launch

```REDIS_HOST=172.17.0.1 REDIS_PORT=6379 REDIS_PASSWORD=redis BUILD_TOKEN=token sidekiq -c 1 -q publish_worker -q publish_worker_default -r ./lib/abf-worker.rb```

Container must have platforms mounted in /share/platforms


How to perfom publisher database unlock

on abfui:
```source envfile; cd rosa-build; rails console```
and in console:
```RepositoryStatus.where.not(status: 0).each do |a| a.ready end```
