import web

import settings
from libs import iredutils
from libs.panel import LOG_EVENTS

session = web.config.get('_session')


def list_logs(cur_page=1):

    # Get number of total records.
    qr = web.conn_fail2ban.select('banned', what='COUNT(id) AS total')

    total = qr[0].total or 0

    # Get records.
    qr = web.conn_fail2ban.select(
        'banned',
        offset=(cur_page - 1) * settings.PAGE_SIZE_LIMIT,
        limit=settings.PAGE_SIZE_LIMIT,
        order='timestamp DESC',
    )
    return (total, list(qr))


def delete_logs(form, delete_all=False):
    if delete_all:
        try:
            web.conn_fail2ban.update('banned', remove=1)
            return (True, )
        except Exception as e:
            return (False, repr(e))
    else:
        ids = form.get('id', [])

        if ids:
            try:
                web.conn_fail2ban.update('banned', where="id IN %s" % web.db.sqlquote(ids), remove=1)
                return (True, )
            except Exception as e:
                return (False, repr(e))

    return (True, )