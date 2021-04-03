# Author: Avinash Karhana <avinashkarahan1@gmail.com>

from libs.regxes import email as e, domain as d

urls = [
    # Make url ending with or without '/' going to the same class.
    '/(.*)/', 'controllers.utils.Redirect',
    '/api', 'controllers.api.msg.Message',

    # User related LIST functions
    '/api/users/(%s$)' % d, 'controllers.api.user.List',
    
    # GET disabled accounts.
    '/api/users/(%s)/disabled' % d, 'controllers.api.user.ListDisabled',
    
    # Create user.
    '/api/user/create/(%s$)' % d, 'controllers.api.user.Create',
    
    # Profile Functions.
    '/api/user/profile/(%s$)' % e, 'controllers.api.user.Profile',
]
