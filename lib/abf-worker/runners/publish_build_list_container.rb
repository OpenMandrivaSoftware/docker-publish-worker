require 'abf-worker/models/repository'

module AbfWorker::Runners
  class PublishBuildListContainer

    attr_accessor :script_pid

    def initialize(worker, options)
      @worker       = worker
      @cmd_params       = options['cmd_params'] + " PLATFORM_PATH=" + options['platform']['platform_path']
      @platform_type    = options['platform']['type']
      @main_script      = options['main_script']
      @rollback_script  = options['rollback_script']
      @repository   = options['repository']
      @packages     = options['packages'] || {}
      @old_packages = options['old_packages'] || {}
    end

    def rollback
      if @rollback_script
        run_script true
      end
    end

    def run_script(rollback_activity = false)
      init_packages_lists
      init_gpg_keys unless rollback_activity
      puts "Run #{rollback_activity ? 'rollback activity ' : ''}script..."

      command = base_command_for_run
      script_name = rollback_activity ? @rollback_script : @main_script
      command << script_name
      output_folder = APP_CONFIG['output_folder']
      Dir.mkdir(output_folder) if not Dir.exists?(output_folder)
      if @worker.status != AbfWorker::BaseWorker::BUILD_CANCELED
        exit_status = nil
        @script_pid = Process.spawn(command.join(' '), [:out,:err]=>[output_folder + "/publish_" + script_name + ".log", "w"])
        Process.wait(@script_pid)
        exit_status = $?.exitstatus
        if @worker.status != AbfWorker::BaseWorker::BUILD_CANCELED
          if exit_status.nil? or exit_status != 0
            @worker.status = AbfWorker::BaseWorker::BUILD_FAILED
            rollback
          else
            @worker.status = AbfWorker::BaseWorker::BUILD_COMPLETED
          end
        end
      end
    end

    private

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

      system 'rm -rf ' + ROOT + '/container/*'
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
