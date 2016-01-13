require 'resque'

env = ENV['ENV'] || 'development'
resque_config = YAML.load_file("#{ROOT}/config/resque.yml")[env]
Resque.redis  = Redis.new(host:        resque_config.gsub(/\:.*$/, ''),
                          port:        resque_config.gsub(/.*\:/, ''),
                          password:    'redis',
                          driver:      :hiredis,
                          timeout:     30)
