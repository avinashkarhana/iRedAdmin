# Author: Avinash Karhana <avinashkarahan1@gmail.com>

from libs.regxes import email as e, domain as d

urls = [
    # Make url ending with or without '/' going to the same class.
    '/(.*)/', 'controllers.utils.Redirect',
    '/api', 'controllers.api.msg.Message',

    # User related LIST functions
    '/api/users/(%s$)' % d, 'controllers.sql.user.List',
    
    # GET disabled accounts.
    '/api/users/(%s)/disabled' % d, 'controllers.sql.user.ListDisabled',
    
    # Create user.
    '/api/user/create/(%s$)' % d, 'controllers.sql.user.Create',
    
    # Profile Functions.
    '/api/user/profile/(%s$)' % e, 'controllers.sql.user.Profile',
]
