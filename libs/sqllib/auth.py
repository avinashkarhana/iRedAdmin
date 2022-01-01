import web, datetime, string, re
import settings
from libs import iredutils, iredpwd
from libs.l10n import TIMEZONES
from libs.sqllib import sqlutils

session = web.config.get('_session', {})

# sanitize and remove every char except ascii_letters and digits
def check_api_key_sanitization(s):
    if re.match(r"^[a-zA-Z0-9]+$",s):
        return s
    else:
        return ""

def auth(conn,
         username=False,
         password=False,
         is_api_login=False,
         api_key=False,
         account_type='admin',
         verify_password=False):
    result=False
    kresult={}

    # validate username, password and extract domain from username, if not API login
    if is_api_login==False:
        if not iredutils.is_email(username):
            return (False, 'INVALID_USERNAME')

        if not password:
            return (False, 'EMPTY_PASSWORD')

        username = str(username).lower()
        password = str(password)
        domain = username.split('@', 1)[-1]
    
    #if API login, get api_key string and check_api_key_sanitization
    else:
        if len(str(api_key).strip()) != 256:
            api_key=""
            session.kill()
            return (False, 'INVALID_API_KEY')
        else:
            api_key = check_api_key_sanitization(str(api_key))
            if api_key == "":
                session.kill()
                return (False, 'INVALID_API_KEY')


    # Query database for accounts
    # if not API login and account_type is set to 'admin'
    if account_type == 'admin' and not is_api_login:
        # query admin table for account
        result = conn.select('admin',
                             vars={'username': username},
                             where="username=$username AND active=1",
                             what='password, language, settings',
                             limit=1)

        # if account not found in admin table, query mailbox table ,in case mail user is marked as domain admin
        if not result:
            result = conn.select(
                'mailbox',
                vars={'username': username},
                where="username=$username AND isglobaladmin=1 AND active=1",
                what='password, language, isadmin, isglobaladmin, settings',
                limit=1,
            )

            #if account found set admin_is_mail_user session
            if result:
                session['admin_is_mail_user'] = True
    
    # if not API login and account_type is set to 'user'
    elif account_type == 'user' and not is_api_login:
        # query mailbox table for account
        result = conn.select('mailbox',
                             vars={'username': username},
                             what='password, language, isadmin, isglobaladmin, settings',
                             where="username=$username AND isglobaladmin=1 AND active=1",
                             limit=1)

    # if API login and account_type is set to 'admin'                     
    elif account_type == 'admin' and is_api_login:
        # query api table for given api_key
        key_sql = "SELECT * FROM api where api_key='"+api_key+"' AND is_enabled=1 AND isglobaladminapi=1"
        result = conn.query(key_sql)

        # if api_key not fount, then kill session and push INVALID_API_KEY message
        if len(result)==0:
            session.kill()
            return (False, 'INVALID_API_KEY')
        
        # get current time
        now=datetime.datetime.now()
        kresult=dict(result[0])
        
        # if api_key has expired, then kill session and set the key in database to be disabled and push INVALID_API_KEY message
        if  kresult.get('expiry_date_time') < now :
            conn.update('api', where="kid="+str(kresult.get('kid')).strip(), is_enabled = "0")
            session.kill()
            return (False, 'INVALID_API_KEY')
        # if api_key is disabled, then kill session and push INVALID_API_KEY message
        if str(kresult.get('is_enabled')).strip()=="0":
            session.kill()
            return (False, 'INVALID_API_KEY')

    # if account_type is invalid or Key is invalid
    else:
        # if not API login push INVALID_ACCOUNT_TYPE messgae, else push INVALID_API_KEY message
        if not is_api_login:
            return (False, 'INVALID_ACCOUNT_TYPE')
        else:
            return (False, 'INVALID_API_KEY')
    
    # Account not found, push INVALID_CREDENTIALS message
    if not result:
        # Do NOT return msg like 'Account does not ***EXIST***', crackers can use it to verify valid accounts.
        return (False, 'INVALID_CREDENTIALS')

    account_settings=""
    record=""

    # get user account settings if not API login
    if not is_api_login:
        record = result[0]
        account_settings = sqlutils.account_settings_string_to_dict(str(record.settings))
    # get API account settings if API login
    else:
        record= kresult
        account_settings = sqlutils.account_settings_string_to_dict(str(record.get('settings')))
    
    # Verify password, if not API login
    if not is_api_login:
        password_sql = str(record.password)
        if not iredpwd.verify_password_hash(password_sql, password):
            return (False, 'INVALID_CREDENTIALS')

    # set is_global_admin, is_global_admin_api, global_admin_api_key in session, if KEY is of type 'isglobaladminapi'
    if record.get('isglobaladminapi', 0) == 1:
        session['is_global_admin'] = True
        session['is_global_admin_api'] = True
        session['global_admin_api_key'] = api_key

    # if Not API login set username, lang, timezone, is_global_admin, is_admin in session for users
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

        # Set session['is_global_admin'] if admin is a mail user
        if session.get('admin_is_mail_user'):
            if record.get('isglobaladmin', 0) == 1:
                session['is_global_admin'] = True
            if record.get('isadmin', 0) == 1:
                session['is_admin'] = True

        # set session for 'is_global_admin', 'is_admin' if admin is domain_admin
        else:
            # find global admin with domain admin with domains ALL
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

            # if not global admin but domain admin and not a mail user
            try:
                result = conn.select('domain_admins',
                                     vars={'username': username},
                                     what='domain',
                                     where='username=$username',
                                    )
                if result:
                    session['is_admin'] = True
            except:
                pass

    #set logged, cookie_name, cookie_name, ignore_expiry in session
    session['logged'] = True
    web.config.session_parameters['cookie_name'] = 'iRedAdmin'
    web.config.session_parameters['ignore_change_ip'] = settings.SESSION_IGNORE_CHANGE_IP
    web.config.session_parameters['ignore_expiry'] = False
    
    # return authentication
    return (True, {'account_settings': account_settings})
