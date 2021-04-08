import web
import settings
from controllers import decorators
from libs.panel import fail2ban as fail2banlib
from libs.logger import log_activity

session = web.config.get('_session')

if settings.backend == 'ldap':
    from libs.ldaplib.core import LDAPWrap
    from libs.ldaplib import admin as ldap_lib_admin
elif settings.backend in ['mysql', 'pgsql']:
    from libs.sqllib import SQLWrap, admin as sql_lib_admin


class Log:
    @decorators.require_login
    @decorators.require_admin
    def GET(self):
        form = web.input(_unicode=False)

        # Get queries.
        form_cur_page = web.safestr(form.get('page', '1'))

        if not form_cur_page.isdigit() or form_cur_page == '0':
            form_cur_page = 1
        else:
            form_cur_page = int(form_cur_page)

        total, entries = fail2banlib.list_logs(cur_page=form_cur_page)

        return web.render('panel/fail2ban.html',
                          cur_page=form_cur_page,
                          total=total,
                          entries=entries,
                          msg=form.get('msg'))

    @decorators.require_global_admin
    @decorators.csrf_protected
    @decorators.require_global_admin
    def POST(self):
        form = web.input(_unicode=False, id=[], ip=[])
        action = form.get('action', 'delete')

        delete_all = False
        if action == 'deleteAll':
            delete_all = True

        qr = fail2banlib.delete_logs(form=form, delete_all=delete_all)
        if qr[0]:
            if not delete_all:
                for i in form.ip:
                    log_activity(msg="Unbanned "+i, event='unban')
                raise web.seeother('/activities/fail2ban?msg=UNBANNED')
            else:
                log_activity(msg="Unbanned All", event='unban')
                raise web.seeother('/activities/fail2ban?msg=UNBANNED_ALL')
        else:
            raise web.seeother('/activities/fail2ban?msg=%s' % web.urlquote(qr[1]))
