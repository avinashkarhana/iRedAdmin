# Author: Zhang Huangbin <zhb@iredmail.org>

from controllers import decorators as base_decorators

require_login = base_decorators.require_login
require_admin = base_decorators.require_admin
require_global_admin = base_decorators.require_global_admin
require_global_admin_api_key = base_decorators.require_global_admin_api_key
csrf_protected = base_decorators.csrf_protected

