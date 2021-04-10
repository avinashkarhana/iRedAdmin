# Author: Avinash Karhana <avinashkarahan1@gmail.com>

import web
import datetime,string,secrets,re
import urllib.parse
import settings
from controllers import decorators
from libs.sqllib import SQLWrap
from libs.logger import log_activity

session = web.config.get('_session')
PAGE_SIZE_LIMIT = settings.PAGE_SIZE_LIMIT
PAGE_SIZE_LIMIT = 5

class APIs:
    @decorators.require_global_admin
    def GET(self, generate=False):
        form = web.input(_unicode=False)
        
        _wrap = SQLWrap()
        conn = _wrap.conn

        if not generate: 
            # Get queries.
            form_cur_page = web.safestr(form.get('page', '1'))

            if not form_cur_page.isdigit() or form_cur_page == '0':
                form_cur_page = 1
            else:
                form_cur_page = int(form_cur_page)

            qr= conn.select('api', what='COUNT(kid) AS total')

            total = qr[0].total or 0
            entries=[]
            # Get records.
            if total>0:
                qr = conn.select('api',
                    offset=(form_cur_page - 1) * PAGE_SIZE_LIMIT,
                    limit=PAGE_SIZE_LIMIT,
                    order='is_enabled DESC, expiry_date_time DESC, last_update_timestamp DESC,creation_timestamp DESC',
                )
                entries=list(qr)
                for i in range(len(entries)):
                    if datetime.datetime.strptime(str(entries[i].expiry_date_time), '%Y-%m-%d %H:%M:%S') > datetime.datetime.now():
                        entries[i]['editable']=True
                    else:
                        entries[i]['editable']=False
                    entries[i].api_description=urllib.parse.unquote(entries[i].api_description)
            

            return web.render('panel/apis.html',
                            cur_page=form_cur_page,
                            total=total,
                            entries=entries,
                            page_size_limit=PAGE_SIZE_LIMIT,
                            msg=form.get('msg'))
    
        else:
            return web.render('panel/apis_gen.html')

    @decorators.require_global_admin
    @decorators.csrf_protected
    def POST(self,generate=False):
        form = web.input(_unicode=False, id=[], key=[])
        action = form.get('action', 'delete')
        delete_all = False
        _wrap = SQLWrap()
        conn = _wrap.conn
        # initailize query result variable
        qr = ()
        api_key=""

        if action in ['deleteAll','delete'] and not generate:
            if action=="deleteAll":
                delete_all = True

            if delete_all:
                try:
                    last_update_timestamp=str(str(datetime.datetime.now()).split(".")[0])
                    conn.update('api', where="", is_enabled=0, last_update_timestamp=last_update_timestamp)
                    qr = (True, )
                except Exception as e:
                    qr = (False, repr(e))
            else:
                ids = form.get('id', [])

                if ids:
                    last_update_timestamp=str(str(datetime.datetime.now()).split(".")[0])
                    try:
                        conn.update('api', where="kid IN %s" % web.db.sqlquote(ids), is_enabled=0, last_updated_by=session.get('username'), last_update_timestamp=last_update_timestamp)
                        qr = (True, )
                    except Exception as e:
                        qr = (False, repr(e))
                else:
                    qr = (False,"No API Keys Selected!")

        elif action == "generate" and generate:
            alphabet = string.ascii_letters + string.digits
            api_key = ''.join(secrets.choice(alphabet) for i in range(256))
            exp_date = str(form.get("expiry","")).strip()
            is_enabled = form.get("is_enabled","")
            isglobaladminapi = form.get("isglobaladminapi","")
            generated_by = session.get("username")
            
            # input validation checks
            if len(api_key)!=256: api_key=""
            if str(is_enabled).strip() not in ["0","1"]: is_enabled=""
            if str(isglobaladminapi).strip() not in ["0","1"]: isglobaladminapi=""
            api_description=""
            try:
                api_description = form.get("api_description","")
                api_description = api_description.replace(chr(10)," ").strip()
                api_description = api_description.replace(chr(13)," ").strip()
                api_description = re.sub(' +', ' ',api_description).strip()
                api_description = urllib.parse.quote(api_description,safe='')
            except:
                api_description=""
            last_update_timestamp=str(str(datetime.datetime.now()).split(".")[0])
            if len(api_description)>256:
                api_description = api_description[:256]

            if generated_by is None: generated_by=""
            try:
                datetime.datetime.strptime(exp_date, '%Y-%m-%d %H:%M:%S')
            except:
                exp_date=""
                
            if api_key!="" and exp_date!="" and is_enabled!="" and isglobaladminapi!="" and generated_by != "":
                try:
                    conn.insert('api',
                        api_description=api_description,
                        api_key=api_key,
                        expiry_date_time=exp_date,
                        is_enabled=is_enabled,
                        isglobaladminapi=isglobaladminapi,
                        generated_by=generated_by,
                        last_update_timestamp=last_update_timestamp,
                    )
                    qr = (True,)
                except Exception as e:
                    qr = (False, repr(e))
            else:
                qr = (False, "Missing or incorrect parameters")
        
        elif action == "update":
            updation={}
            form_ids=form.get('id', [])
            for i in form_ids:
                updation[i]={}
                api_description=""
                try:
                    api_description = form.get(i+"_api_description","")
                    api_description = api_description.replace(chr(10)," ").strip()
                    api_description = api_description.replace(chr(13)," ").strip()
                    api_description = re.sub(' +', ' ',api_description).strip()
                    api_description = urllib.parse.quote(api_description,safe='')
                    if len(api_description)>256:
                        api_description = api_description[:256]
                except:
                    api_description=""
                try:
                    enb = form.get(i+'_is_enabled', None)
                    isglbl = form.get(i+'_isglobaladminapi',None)
                    updation[i]={"is_enabled":enb,"isglobaladminapi":isglbl}
                except:
                    pass

                if updation[i].get('is_enabled') != None and updation[i].get('is_enabled') != "" and updation[i].get('isglobaladminapi') != None and updation[i].get('isglobaladminapi') != "":
                    try:
                        enbld=int(updation[i].get('is_enabled'))
                        glbladmnapi=int(updation[i].get('isglobaladminapi'))
                    except:
                        pass
                    if (enbld in [0,1]) and (glbladmnapi in [0,1]):
                        last_update_timestamp=str(str(datetime.datetime.now()).split(".")[0])
                        try:
                            if api_description=="":
                                conn.update('api', where="kid = %s" % web.db.sqlquote(i), is_enabled=enbld, isglobaladminapi=glbladmnapi, last_updated_by=session.get('username'), last_update_timestamp=last_update_timestamp)
                            else:    
                                conn.update('api', where="kid = %s" % web.db.sqlquote(i), is_enabled=enbld, isglobaladminapi=glbladmnapi, last_updated_by=session.get('username'), last_update_timestamp=last_update_timestamp, api_description=api_description)
                        except Exception as e:
                            qr = (False, repr(e))

            updation={}
            del updation
            qr = (True, )

        else:
                raise web.seeother('/apis?msg=INVALID_ACTION')

        if qr[0]:
            if action in ['deleteAll','delete']:
                if not delete_all:
                    for i in form.key:
                        log_activity(msg="Disabled API Key "+i, event='disable_api_key')
                    raise web.seeother('/apis?msg=DISABLED_API_KEY')
                else:
                    log_activity(msg="Disabled all API Keys", event='disable_api_key')
                    raise web.seeother('/apis?msg=DISABLED_API_KEY_ALL')
            elif action == "generate":
                log_activity(msg="GENERATED API Key "+api_key, event='generated_api_key')
                raise web.seeother('/apis?msg=GENERATED_API_KEY_'+api_key)
            elif action == "update":
                idsl = list(form.get('id', []))
                idsl=", ".join(map(str, idsl))
                log_activity(msg="Updated API Keys with ids: "+idsl, event='updated_api_key')
                raise web.seeother('/apis?msg=UPDATED_API_KEY')
            else:
                raise web.seeother('/apis?msg=INVALID_ACTION')
        else:
            raise web.seeother('/apis?msg=%s' % web.urlquote(qr[1]))

