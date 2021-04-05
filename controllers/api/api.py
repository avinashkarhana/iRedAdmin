import datetime
from libs.sqllib import SQLWrap

def api_key_is_valid(api_key):

    _wrap = SQLWrap()
    conn = _wrap.conn

    key_sql = "SELECT * FROM api where api_key='"+api_key+"' AND is_enabled=1 AND isglobaladminapi=1"
    result = conn.query(key_sql)
    
    if len(result)==0:
        return False
    
    now=datetime.datetime.now()
    kresult=dict(result[0])
    
    if  kresult.get('expiry_date_time') < now :
        conn.update('api', where="kid="+str(kresult.get('kid')).strip(), is_enabled = "0")
        return False

    if str(kresult.get('is_enabled')).strip()=="0":
        return False

    return True