import web, datetime
import settings
from libs import iredutils, iredpwd
from libs.l10n import TIMEZONES
from libs.sqllib import sqlutils

session = web.config.get('_session', {})


def auth(conn,
         username=False,
         password=False,
         is_api_login=False,
         api_key=False,
         account_type='admin',
         verify_password=False):
    # Check if Username/Password login
    result=False
    kresult={}
    if is_api_login==False:
        if not iredutils.is_email(username):
            return (False, 'INVALID_USERNAME')

        if not password:
            return (False, 'EMPTY_PASSWORD')

        username = str(username).lower()
        password = str(password)
        domain = username.split('@', 1)[-1]
    #if API login
    else:
        api_key = str(api_key)


    # Query account from SQL database.
    if account_type == 'admin' and not is_api_login:
        # separate admin accounts
        result = conn.select('admin',
                             vars={'username': username},
                             where="username=$username AND active=1",
                             what='password, language, settings',
                             limit=1)

        # mail user marked as domain admin
        if not result:
            result = conn.select(
                'mailbox',
                vars={'username': username},
                where="username=$username AND active=1 AND (isadmin=1 OR isglobaladmin=1)",
                what='password, language, isadmin, isglobaladmin, settings',
                limit=1,
            )
            if result:
                session['admin_is_mail_user'] = True
    elif account_type == 'user' and not is_api_login:
        result = conn.select('mailbox',
                             vars={'username': username},
                             what='password, language, isadmin, isglobaladmin, settings',
                             where="username=$username AND active=1",
                             limit=1)

    # check api key if is_api_login                         
    elif is_api_login and account_type == 'admin':
        key_sql = "SELECT * FROM api where api_key='"+api_key+"' AND is_enabled=1 AND isglobaladminapi=1"
        result = conn.query(key_sql)

        if len(result)==0:
            session.kill()
            return (False, 'INVALID_API_KEY')
        
        now=datetime.datetime.now()
        kresult=dict(result[0])
        
        if  kresult.get('expiry_date_time') < now :
            conn.update('api', where="kid="+str(kresult.get('kid')).strip(), is_enabled = "0")
            session.kill()
            return (False, 'INVALID_API_KEY')

        if str(kresult.get('is_enabled')).strip()=="0":
            session.kill()
            return (False, 'INVALID_API_KEY')


    else:
        if not is_api_login:
            return (False, 'INVALID_ACCOUNT_TYPE')
        else:
            return (False, 'INVALID_API_KEY')
    
    if not result:
        # Account not found.
        # Do NOT return msg like 'Account does not ***EXIST***', crackers
        # can use it to verify valid accounts.
        return (False, 'INVALID_CREDENTIALS')

    account_settings=""
    record=""
    if not is_api_login:
        record = result[0]
        account_settings = sqlutils.account_settings_string_to_dict(str(record.settings))
    else:
        record= kresult
        account_settings = sqlutils.account_settings_string_to_dict(str(record.get('settings')))
    
    # Verify password
    if not is_api_login:
        password_sql = str(record.password)
        if not iredpwd.verify_password_hash(password_sql, password):
            return (False, 'INVALID_CREDENTIALS')

    if record.get('isglobaladminapi', 0) == 1:
        session['is_global_admin'] = True
        session['is_global_admin_api'] = True
        session['global_admin_api_key'] = api_key


    if (not verify_password) and (not is_api_login):
        session['username'] = username

        # Set preferred language.
        session['lang'] = web.safestr(record.get('language', settings.default_language))

        # Set timezone (GMT-XX:XX).
        # Priority: per-user timezone > per-domain > global setting
        timezone = settings.LOCAL_TIMEZONE

        if 'timezone' in account_settings:
            tz_name = account_settings['timezone']
            if tz_name in TIMEZONES:
                timezone = TIMEZONES[tz_name]
        else:
            # Get per-domain timezone
            qr_domain = conn.select('domain',
                                    vars={'domain': domain},
                                    what='settings',
                                    where='domain=$domain',
                                    limit=1)
            if qr_domain:
                domain_settings = sqlutils.account_settings_string_to_dict(str(qr_domain[0]['settings']))
                if 'timezone' in domain_settings:
                    tz_name = domain_settings['timezone']
                    if tz_name in TIMEZONES:
                        timezone = TIMEZONES[tz_name]

        session['timezone'] = timezone

        # Set session['is_global_admin']
        if session.get('admin_is_mail_user'):
            if record.get('isglobaladmin', 0) == 1:
                session['is_global_admin'] = True
                session['is_admin'] = True
            if record.get('isadmin', 0) == 1:
                session['is_admin'] = True

        else:
            try:
                result = conn.select('domain_admins',
                                     vars={'username': username, 'domain': 'ALL'},
                                     what='domain',
                                     where='username=$username AND domain=$domain',
                                     limit=1)
                if result:
                    session['is_global_admin'] = True
                    session['is_admin'] = True
            except:
                pass

    session['logged'] = True
    web.config.session_parameters['cookie_name'] = 'iRedAdmin'
    web.config.session_parameters['ignore_change_ip'] = settings.SESSION_IGNORE_CHANGE_IP
    web.config.session_parameters['ignore_expiry'] = False

    return (True, {'account_settings': account_settings})
