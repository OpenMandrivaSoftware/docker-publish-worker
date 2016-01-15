require 'forwardable'
require 'abf-worker/models/repository'

module AbfWorker::Runners
  class PublishBuildListContainer
    extend Forwardable

    attr_accessor :script_runner,
                  :can_run

    def_delegators :@worker, :logger

    def initialize(worker, options)
      @worker       = worker
      @cmd_params       = options['cmd_params']
      @platform_type    = options['platform']['type']
      @main_script      = options['main_script']
      @rollback_script  = options['rollback_script']
      @repository   = options['repository']
      @packages     = options['packages'] || {}
      @old_packages = options['old_packages'] || {}
      @can_run      = true
    end

    def run_script
      @script_runner = Thread.new{ run_build_script }
      @script_runner.join if @can_run
    end

    def rollback
      if @rollback_script
        run_build_script true
      end
    end

    private

    def run_build_script(rollback_activity = false)
      init_packages_lists
      init_gpg_keys unless rollback_activity
      puts "Run #{rollback_activity ? 'rollback activity ' : ''}script..."

      command = base_command_for_run
      command << (rollback_activity ? @rollback_script : @main_script)
      exit_status = nil
      process = IO.popen(command.join(' '), "r") do |io|
        loop do
          break if io.eof
          puts io.gets
        end
        exit_status = $?.exitstatus
      end
      @worker.status = exit_status == 0 ? AbfWorker::BaseWorker::BUILD_COMPLETED : AbfWorker::BaseWorker::BUILD_FAILED
      # No logs on publishing build_list
      # save_results 
    end

    def base_command_for_run
      [
        'cd ' + ROOT + '/scripts/' + @platform_type + ';',
        'sudo ',
        @cmd_params,
        ' /bin/bash '
      ]
    end

    def init_packages_lists
      puts 'Initialize lists of new and old packages...'

      [@packages, @old_packages].each_with_index do |packages, index|
        prefix = index == 0 ? 'new' : 'old'
        add_packages_to_list packages['sources'], "#{prefix}.SRPMS.list"
        (packages['binaries'] || {}).each do |arch, list|
          add_packages_to_list list, "#{prefix}.#{arch}.list"
        end
      end
    end

    def add_packages_to_list(packages = [], list_name)
      return if packages.nil? || packages.empty?
      Dir.mkdir(ROOT + '/container') if not Dir.exists?(ROOT + '/container')
      file = File.open(ROOT + "/container/#{list_name}", "w")
      packages.each{ |p| file.puts p }
      file.close
    end

    def init_gpg_keys
      return
      repository = AbfWorker::Models::Repository.find_by_id(@repository['id']) if @repository
    end

  end
end
