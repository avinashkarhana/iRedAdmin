# Author: Avinash Karhana <avinashkarahan1@gmail.com>

import web
import settings

class Message:
    def GET(self):
        inputs=web.input()
        msg={}
        try:
            msg['msg']=inputs.msg
            msg['is_msg_set']=True
        except AttributeError:
            msg['msg']="Default Message"
            msg['is_msg_set']=False
        return web.render('api/msg/msg.html', content_type="application/json", msg=msg)