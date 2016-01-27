require 'abf-worker/runners/publish_build_list_container'
require 'abf-worker/inspectors/live_inspector'

module AbfWorker
  class PublishWorker < BaseWorker
    @queue = :publish_worker

    attr_accessor :runner

    def self.perform(options)
      self.new(options).perform
    end

    protected

    def initialize(options)
      @observer_queue       = 'publish_observer'
      @observer_class       = 'AbfWorker::PublishObserver'
      @build_list_ids       = options['build_list_ids']
      @projects_for_cleanup = options['projects_for_cleanup']
      super options
      @runner = AbfWorker::Runners::PublishBuildListContainer.new(self, options)
      initialize_live_inspector(options['time_living'])
    end

    def send_results
      options = { projects_for_cleanup: @projects_for_cleanup }
      options.merge!({
        results:        upload_results_to_file_store,
        build_list_ids: @build_list_ids
      }) unless @skip_feedback
      update_build_status_on_abf(options, true)
    end

  end

  class PublishWorkerDefault < PublishWorker
    @queue = :publish_worker_default
  end

end
