require 'config_for'

env = ENV['ENV'] || 'development'

ROOT = File.dirname(__FILE__) + '/../../../'

APP_CONFIG = ConfigFor.load_config!("#{ROOT}/config", 'application', env)
APP_CONFIG['env'] = env