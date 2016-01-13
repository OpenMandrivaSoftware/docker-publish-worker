require 'net/ssh'
require 'abf-worker/outputters/logger'
require 'abf-worker/outputters/live_outputter'
require 'socket'

module AbfWorker
  class BaseWorker
    include Log4r

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
                  :logger_name,
                  :shutdown,
                  :url_to_build

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
      cleanup
    end

    def print_error(e)
      self.class.send_error e, {
        hostname:   Socket.gethostname,
        worker_id:  @worker_id,
        options:    @options
      }
      a = []
      a << '==> ABF-WORKER-ERROR-START'
      a << 'Something went wrong, report has been sent to ABF team, please try again.'
      a << 'If this error will be happen again, please inform us using https://abf.rosalinux.ru/contact'
      a << '----------'
      a << e.message.gsub(*AbfWorker::Outputters::Logger::FILTER)
      a << e.backtrace.join("\n")
      a << '<== ABF-WORKER-ERROR-END'
      logger.error a.join("\n")
    end


    def self.send_error(e, params = {})
      Airbrake.notify(e, parameters: params) if APP_CONFIG['env'] == 'production'
      puts e.message.gsub(*AbfWorker::Outputters::Logger::FILTER)
      puts e.backtrace.join("\n")
    end

    def logger
      @logger || init_logger('abfworker::base-worker')
    end

    protected

    def url_to_build
      return @url_to_build if @url_to_build
      #path = runner.is_a?(AbfWorker::Runners::Iso) ? 'product_build_lists' : 'build_lists'
      path = 'build_lists'
      @url_to_build = "#{APP_CONFIG['abf_url']}/#{path}/#{@build_id}"
    end

    def file_store_token
      @file_store_token ||= APP_CONFIG['file_store']['token']
    end

    def upload_file_to_file_store(path, file_name)
      path_to_file = path + '/' + file_name
      return unless File.file?(path_to_file)
      if file_name =~ /.log$/
        tmp_file = "#{path_to_file}.tmp"
        File.open(tmp_file, 'w') do |f|
          f.puts "==> See: '#{url_to_build}'"
          f.puts ''
          File.foreach(path_to_file){ |li| f.puts li }
        end
        File.rename tmp_file, path_to_file
      end

      # Compress the log when file size more than 10MB
      file_size = (File.size(path_to_file).to_f / TWO_IN_THE_TWENTIETH).round(2)
      if file_name =~ /.log$/ && file_size >= 10
        system "tar -zcvf #{path_to_file}.tar.gz #{path_to_file}"
        File.delete path_to_file
        path_to_file << '.tar.gz'
        file_name << '.tar.gz'
      end

      logger.log "Uploading file '#{file_name}'...."
      sha1 = Digest::SHA1.file(path_to_file).hexdigest

      # curl --user myuser@gmail.com:mypass -POST -F "file_store[file]=@files/archive.zip" http://file-store.rosalinux.ru/api/v1/file_stores.json
      if %x[ curl #{APP_CONFIG['file_store']['url']}.json?hash=#{sha1} ] == '[]'
        command = 'curl --user '
        command << file_store_token
        command << ': -POST -F "file_store[file]=@'
        command << path_to_file
        command << '" '
        command << APP_CONFIG['file_store']['create_url']
        command << ' --connect-timeout 5 --retry 5'
        logger.log %x[ #{command} ]
      end

      # File.delete path_to_file
      system "sudo rm -rf #{path_to_file}"
      logger.log 'Done.'
      {:sha1 => sha1, :file_name => file_name, :size => file_size}
    end

    def upload_results_to_file_store
      uploaded = []
      results_folder = APP_CONFIG["output_folder"]
      if File.exists?(results_folder) && File.directory?(results_folder)
        Dir.new(results_folder).entries.each do |f|
          uploaded << upload_file_to_file_store(results_folder, f)
        end
      end
      uploaded.compact
    end

    def cleanup
      return unless @logger
      @logger.outputters.select{ |o| o.is_a?(AbfWorker::Outputters::LiveOutputter) }.each do |o|
        o.stop
      end
    end

    def initialize_live_inspector(time_living)
      @live_inspector = AbfWorker::Inspectors::LiveInspector.new(self, time_living)
      @live_inspector.run
    end

    def init_logger(logger_name = nil)
      @logger_name = logger_name
      @logger = AbfWorker::Outputters::Logger.new @logger_name
      @logger.outputters << Log4r::Outputter.stdout

      # see: https://github.com/colbygk/log4r/blob/master/lib/log4r/formatter/patternformatter.rb#L22
      formatter = Log4r::PatternFormatter.new(pattern: "%m")
      unless @skip_feedback
        @logger.outputters << Log4r::FileOutputter.new(
          @logger_name, { filename: "log/#{@logger_name}.log", formatter: formatter }
        )

        @logger.outputters << AbfWorker::Outputters::LiveOutputter.new(
          @logger_name, { formatter: formatter, worker: self}
        )
      end
      @logger
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
