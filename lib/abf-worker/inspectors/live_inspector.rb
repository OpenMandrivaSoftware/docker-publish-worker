require 'time'

module AbfWorker::Inspectors
  class LiveInspector
    CHECK_INTERVAL = 60 # 60 sec

    def initialize(worker, time_living)
      @worker       = worker
      @kill_at      = Time.now + time_living.to_i
    end

    def run
      @thread = Thread.new do
        while true
          begin
            sleep CHECK_INTERVAL
            stop_build if kill_now?
          rescue => e
          end
        end
      end
      Thread.current[:subthreads] << @thread
    end

    private

    def kill_now?
      @kill_at < Time.now
    end

    def stop_build
      @worker.status = AbfWorker::BaseWorker::BUILD_CANCELED
      runner = @worker.runner
      script_pid = runner.script_pid
      if script_pid
        Process.kill(:TERM, script_pid)
        runner.rollback if runner.respond_to?(:rollback)
      end
    end

  end
end
