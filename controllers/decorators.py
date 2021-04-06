import web,urllib
from libs import iredutils
from controllers.api.api import api_key_is_valid

session = web.config.get("_session")


def require_login(func):
    def proxyfunc(*args, **kw):
        if session.get("logged") is True:
            return func(*args, **kw)
        else:
            session.kill()
            raise web.seeother("/login?msg=LOGIN_REQUIRED")
    return proxyfunc

def require_admin(func):
    def proxyfunc(*args, **kw):
        if session.get("is_admin") is True or session.get("is_global_admin") is True:
            return func(*args, **kw)
        else:
            session.kill()
            raise web.seeother("/login?msg=LOGIN_REQUIRED")
    return proxyfunc


def require_global_admin(func):
    def proxyfunc(*args, **kw):
        if session.get("is_global_admin"):
            if session.get("is_global_admin_api") and not api_key_is_valid(session.get("global_admin_api_key")):
                session.kill()
                raise web.seeother("/api?msg=LOGIN_REQUIRED")
            return func(*args, **kw)
        else:
            if session.get("logged"):
                if session.get("is_global_admin_api") :
                    raise web.seeother("/api?msg=Pobably_Already_LoggedIn_"+urllib.parse.urlencode(session))
                raise web.seeother("/domains?msg=PERMISSION_DENIED")
            else:
                raise web.seeother("/login?msg=LOGIN_REQUIRED")

    return proxyfunc

def require_global_admin_api_key(func):
    def proxyfunc(*args, **kw):
        if session.get("is_global_admin_api"):
            if not api_key_is_valid(session.get("global_admin_api_key")):
                session.kill()
                raise web.seeother("/api?msg=LOGIN_REQUIRED")
            return func(*args, **kw)
        else:
            if session.get("logged"):
                raise web.seeother("/api?msg=PERMISSION_DENIED")
            else:
                raise web.seeother("/api?msg=LOGIN_REQUIRED")

    return proxyfunc


def csrf_protected(f):
    def decorated(*args, **kw):
        form = web.input()

        if "csrf_token" not in form:
            return web.render("error_csrf.html")

        if not session.get("csrf_token"):
            session["csrf_token"] = iredutils.generate_random_strings(32)

        if form["csrf_token"] != session["csrf_token"]:
            return web.render("error_csrf.html")

        return f(*args, **kw)

    return decorated
