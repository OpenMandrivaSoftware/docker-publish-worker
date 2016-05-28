require 'config_for'

Thread.abort_on_exception = true

ROOT = File.dirname(__FILE__) + '/../../../'

APP_CONFIG = ConfigFor.load_config!("#{ROOT}/config", 'application', 'common')
Dir.mkdir(APP_CONFIG['output_folder']) if not Dir.exists?(APP_CONFIG['output_folder'])
Dir.mkdir(ROOT + '/container') if not Dir.exists?(ROOT + '/container')