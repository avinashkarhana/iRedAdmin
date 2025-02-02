import web
import settings

from libs import __version__
from libs import iredutils, sysinfo
from libs.logger import log_activity

from libs.sqllib import SQLWrap, auth, decorators
from libs.sqllib import admin as sql_lib_admin

session = web.config.get('_session')


class Login:
    def GET(self):
        form = web.input(_unicode=False)
        is_api_login = False
        
        # check if trying API Login with GET Method
        try:
            if form.get('key', '').strip()!="" and form.get('key', '').strip()!=None:
                is_api_login=True
                api_key = str(form.get('key', '').strip())
            else:
                is_api_login=False
        except AttributeError:
            raise web.seeother('/api?msg=Something_Went_Wrong_E:AuthAPIChk')
        # return if trying API Login with GET Method
        if is_api_login:
            raise web.seeother('/api?msg=Login_with_API_KEY_must_be_via_POST_method')

        if not session.get('logged'):
            form = web.input(_unicode=False)

            if not iredutils.is_allowed_admin_login_ip(client_ip=web.ctx.ip):
                return web.render('error_without_login.html',
                                  error='NOT_ALLOWED_IP')

            # Show login page.
            return web.render('login.html',
                              languagemaps=iredutils.get_language_maps(),
                              msg=form.get('msg'))
        else:
            if settings.REDIRECT_TO_DOMAIN_LIST_AFTER_LOGIN:
                raise web.seeother('/domains')
            else:
                raise web.seeother('/dashboard')

    def POST(self):
        form = web.input(_unicode=False)
        is_api_login = False
        api_key = False
        username = False
        password = False
        login_type='admin'

        # check if API login
        try:
            if form.get('key', '').strip()!="" and form.get('key', '').strip()!=None:
                is_api_login=True
                api_key = str(form.get('key', '').strip()).lower()
                api_key = ''.join(e for e in api_key if e.isalnum())
            else:
                is_api_login=False
        except AttributeError:
            raise web.seeother('/api?msg=Something_Went_Wrong_E:AuthAPIChk')

        # check type of user login
        try:
            if form.get('login_type', '').strip()!="" and form.get('login_type', '').strip()!=None:
                login_type = str(form.get('login_type', '').strip()).lower()
                login_type = ''.join(e for e in login_type if e.isalnum())
        except AttributeError:
            raise web.seeother('/login?msg=Try Again!')
        
        # Get username, password. if not API login
        if not is_api_login:
            username = form.get('username', '').strip().lower()
            password = str(form.get('password', '').strip())

        _wrap = SQLWrap()
        conn = _wrap.conn
        # Authenticate
        auth_result = auth.auth(conn=conn, 
                                username=username,
                                password=password,
                                is_api_login=is_api_login,
                                api_key=api_key,
                                account_type=login_type)
        
        # if Authenticated
        if auth_result[0] is True:
            # Log Activity with correct user type
            if login_type=="admin":
                # Admin loggedin
                log_activity(msg="Admin login success", event='login')
            else:
                # user loggedin
                log_activity(msg="User login success", event='user_login')

            # Save user's selected language and set into session
            selected_language = str(form.get('lang', '')).strip()
            if selected_language != web.ctx.lang and \
               selected_language in iredutils.get_language_maps():
                session['lang'] = selected_language

            # set create_new_domain in session if allowed in users settings
            account_settings = auth_result[1].get('account_settings', {})
            if (not session.get('is_global_admin')) and 'create_new_domains' in account_settings:
                session['create_new_domains'] = True

            # set sessions for disable_viewing_mail_log and disable_managing_quarantined_mails if defined in user settings
            for k in ['disable_viewing_mail_log',
                      'disable_managing_quarantined_mails']:
                if account_settings.get(k) == 'yes':
                    session[k] = True

            # redirect user to /domains if defined in user settings and not API Login, else redirect to dashboard on normal login and push LOGIN_SUCCESSFUL message on API login 
            if settings.REDIRECT_TO_DOMAIN_LIST_AFTER_LOGIN and (not is_api_login):
                raise web.seeother('/domains')
            else:
                if not is_api_login:
                    raise web.seeother('/dashboard?checknew')
                else:
                    raise web.seeother('/api?msg=LOGIN_SUCCESSFUL')

        # if not Authenticated Push Invalid Credentials message
        else:
            if not is_api_login:
                raise web.seeother('/login?msg=INVALID_CREDENTIALS')
            else:
                raise web.seeother('/api?msg=INVALID_CREDENTIALS')


class Logout:
    def GET(self):
        try:
            session.kill()
        except:
            pass

        raise web.seeother('/login')


class Dashboard:
    #@decorators.require_global_admin
    @decorators.require_login
    def GET(self):
        form = web.input(_unicode=False)
        _check_new_version = ('checknew' in form)

        # Check new version.
        if session.get('is_global_admin') and _check_new_version:
            (_status, _info) = sysinfo.check_new_version()
            session['new_version_available'] = _status
            if _status:
                session['new_version'] = _info
            else:
                session['new_version_check_error'] = _info

        # Get numbers of domains, users, aliases.
        num_existing_domains = 0
        num_existing_users = 0

        _wrap = SQLWrap()
        conn = _wrap.conn

        try:
            num_existing_domains = sql_lib_admin.num_managed_domains(conn=conn)
            num_existing_users = sql_lib_admin.num_managed_users(conn=conn)
        except:
            pass

        # Get numbers of existing messages and quota bytes.
        # Set None as default, so that it's easy to detect them in Jinja2 template.
        total_messages = None
        total_bytes = None
        if session.get('is_global_admin'):
            if settings.SHOW_USED_QUOTA:
                try:
                    qr = sql_lib_admin.sum_all_used_quota(conn=conn)
                    total_messages = qr['messages']
                    total_bytes = qr['bytes']
                except:
                    pass

        return web.render(
            'dashboard.html',
            version=__version__,
            iredmail_version=sysinfo.get_iredmail_version(),
            hostname=sysinfo.get_hostname(),
            uptime=sysinfo.get_server_uptime(),
            loadavg=sysinfo.get_system_load_average(),
            netif_data=sysinfo.get_nic_info(),
            # number of existing accounts
            num_existing_domains=num_existing_domains,
            num_existing_users=num_existing_users,
            total_messages=total_messages,
            total_bytes=total_bytes,
        )
