$LOAD_PATH.unshift File.dirname(__FILE__)

require 'abf-worker/initializers/a_app'
require 'abf-worker/initializers/sidekiq'

module AbfWorker
end

require 'abf-worker/publish_worker_default'
