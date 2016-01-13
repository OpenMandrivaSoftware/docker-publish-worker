require 'redis'

class Redis
  def self.connect!
    Redis.current = Redis.new(
      host:   APP_CONFIG['log_server']['host'],
      port:   APP_CONFIG['log_server']['port'],
      driver: :hiredis,
      password: 'redis'
    )
  end
end

Redis.connect!
