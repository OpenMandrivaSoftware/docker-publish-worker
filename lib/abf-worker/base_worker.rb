module AbfWorker
  class BaseWorker

    BUILD_COMPLETED = 0
    BUILD_FAILED    = 1
    BUILD_PENDING   = 2
    BUILD_STARTED   = 3
    BUILD_CANCELED  = 4
    TESTS_FAILED    = 5
    VM_ERROR        = 6
    TWO_IN_THE_TWENTIETH = 2**20

    attr_accessor :status,
                  :build_id,
                  :worker_id,
                  :tmp_dir,
                  :live_inspector,
                  :shutdown

    def initialize(options)
      Thread.current[:subthreads] ||= []
      @shutdown = false
      @options  = options
      @extra    = options['extra'] || {}
      @skip_feedback  = options['skip_feedback'] || false
      @status     = BUILD_STARTED
      @build_id   = options['id']
      @worker_id  = Process.ppid
      update_build_status_on_abf
    end

    def perform
      @runner.run_script
      send_results
    end

    protected

    def initialize_live_inspector(time_living)
      @live_inspector = AbfWorker::Inspectors::LiveInspector.new(self, time_living)
      @live_inspector.run
    end

    def update_build_status_on_abf(args = {}, force = false)
      if !@skip_feedback || force
        worker_args = [{
          id:     @build_id,
          status: (@status == VM_ERROR ? BUILD_FAILED : @status),
          extra:  @extra
        }.merge(args)]

        Resque.push(
          @observer_queue,
          'class' => @observer_class,
          'args'  => worker_args
        )
      end
    end
      
  end
end
