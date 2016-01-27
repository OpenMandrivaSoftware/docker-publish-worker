require 'redis'
require 'resque'

redis_host = ENV['REDIS_HOST']
redis_port = ENV['REDIS_PORT']
redis_password = ENV['REDIS_PASSWORD'].nil? ? '' : ENV['REDIS_PASSWORD']

redis_url = 'redis://:' + redis_password + '@' + redis_host + ':' + redis_port
 
Resque.redis  = Redis.new(url:         redis_url,
                          driver:      :hiredis,
                          timeout:     30)
