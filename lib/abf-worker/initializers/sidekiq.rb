require 'sidekiq'

redis_host = ENV['REDIS_HOST']
redis_port = ENV['REDIS_PORT'].nil? ? '6379' : ENV['REDIS_PORT']
redis_password = ENV['REDIS_PASSWORD'].nil? ? '' : ENV['REDIS_PASSWORD']

raise 'Redis host is not specified' if not redis_host

redis_url = 'redis://:' + redis_password + '@' + redis_host + ':' + redis_port

Sidekiq.configure_client do |config|
  config.redis = { :url => redis_url, :size => 3 }
end

Sidekiq.configure_server do |config|
  config.redis = { :url => redis_url, :size => 3 }
end