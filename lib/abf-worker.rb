require 'abf-worker/initializers/a_app'
require 'abf-worker/initializers/redis'
require 'abf-worker/initializers/resque'

module AbfWorker
	SCRIPTS_ROOT = File.dirname(__FILE__) + '/../scripts'
end

require 'abf-worker/base_worker'
require 'abf-worker/publish_worker'
