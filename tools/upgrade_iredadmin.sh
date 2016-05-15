#!/usr/bin/env bash

# Purpose: Upgrade iRedAdmin from old release.
#          Works with both iRedAdmin open souce edition or iRedAdmin-Pro.

# USAGE:
#
#   # cd /path/to/iRedAdmin-xxx/tools/
#   # bash upgrade_iredadmin.sh

export IRA_HTTPD_USER='iredadmin'
export IRA_HTTPD_GROUP='iredadmin'

export SYS_ROOT_USER='root'

# Check OS to detect some necessary info.
export KERNEL_NAME="$(uname -s | tr '[a-z]' '[A-Z]')"
export UWSGI_RC_SCRIPT_NAME='uwsgi'
export NGINX_PID_FILE='/var/run/nginx.pid'

if [ X"${KERNEL_NAME}" == X"LINUX" ]; then
    export PYTHON_BIN='/usr/bin/python'

    if [ -f /etc/redhat-release ]; then
        # RHEL/CentOS
        export DISTRO='RHEL'
        export HTTPD_SERVERROOT='/var/www'
        export HTTPD_RC_SCRIPT_NAME='httpd'
        export CRON_SPOOL_DIR='/var/spool/cron'
    elif [ -f /etc/lsb-release ]; then
        # Ubuntu
        export DISTRO='UBUNTU'
        if [ -d '/opt/www' ]; then
            export HTTPD_SERVERROOT='/opt/www'
        else
            export HTTPD_SERVERROOT='/usr/share/apache2'
        fi
        export HTTPD_RC_SCRIPT_NAME='apache2'
        export CRON_SPOOL_DIR='/var/spool/cron/crontabs'
    elif [ -f /etc/debian_version ]; then
        # Debian
        export DISTRO='DEBIAN'
        if [ -d '/opt/www' ]; then
            export HTTPD_SERVERROOT='/opt/www'
        else
            export HTTPD_SERVERROOT='/usr/share/apache2'
        fi
        export HTTPD_RC_SCRIPT_NAME='apache2'
        export CRON_SPOOL_DIR='/var/spool/cron/crontabs'
    elif [ -f /etc/SuSE-release ]; then
        # openSUSE
        export DISTRO='SUSE'
        export HTTPD_SERVERROOT='/srv/www'
        export HTTPD_RC_SCRIPT_NAME='apache2'
        export CRON_SPOOL_DIR='/var/spool/cron'
    else
        echo "<<< ERROR >>> Cannot detect Linux distribution name. Exit."
        echo "Please contact support@iredmail.org to solve it."
        exit 255
    fi
elif [ X"${KERNEL_NAME}" == X'FREEBSD' ]; then
    export DISTRO='FREEBSD'
    export HTTPD_SERVERROOT='/usr/local/www'
    export PYTHON_BIN='/usr/local/bin/python'
    if [ -f /usr/local/etc/rc.d/apache24 ]; then
        export HTTPD_RC_SCRIPT_NAME='apache24'
    else:
        export HTTPD_RC_SCRIPT_NAME='apache22'
    fi
    export CRON_SPOOL_DIR='/var/cron/tabs'
elif [ X"${KERNEL_NAME}" == X'OPENBSD' ]; then
    export PYTHON_BIN='/usr/local/bin/python'
    export DISTRO='OPENBSD'
    export HTTPD_SERVERROOT='/var/www'

    export IRA_HTTPD_USER='www'
    export IRA_HTTPD_GROUP='www'
    export CRON_SPOOL_DIR='/var/cron/tabs'
else
    echo "Cannot detect Linux/BSD distribution. Exit."
    echo "Please contact author iRedMail team <support@iredmail.org> to solve it."
    exit 255
fi

export CRON_FILE="${CRON_SPOOL_DIR}/${SYS_ROOT_USER}"

# Optional argument to set the directory which stores iRedAdmin.
if [ $# -gt 0 ]; then
    if [ -d ${1} ]; then
        export HTTPD_SERVERROOT="${1}"
    fi

    if echo ${HTTPD_SERVERROOT} | grep '/iredadmin/*$' > /dev/null; then
        export HTTPD_SERVERROOT="$(dirname ${HTTPD_SERVERROOT})"
    fi
fi

# Dependent package names
# SimpleJson
export DEP_PY_JSON='simplejson'
# BeautifulSoup 4.x
export DEP_PY_BS4='python-beautifulsoup4'
# BeautifulSoup 3.x
export DEP_PY_BS='python-beautifulsoup'
# lxml
export DEP_PY_LXML='python-lxml'
if [ X"${DISTRO}" == X'RHEL' ]; then
    :
elif [ X"${DISTRO}" == X'DEBIAN' -o X"${DISTRO}" == X'UBUNTU' ]; then
    export DEP_PY_JSON='python-simplejson'
    export DEP_PY_BS4='python-beautifulsoup'
elif [ X"${DISTRO}" == X'OPENBSD' ]; then
    export DEP_PY_JSON='py-simplejson'
    export DEP_PY_BS4='py-beautifulsoup4'
    export DEP_PY_BS='py-beautifulsoup4'
elif [ X"${DISTRO}" == X'FREEBSD' ]; then
    export DEP_PY_JSON='devel/py-simplejson'
    export DEP_PY_BS4='www/py-beautifulsoup'
    export DEP_PY_BS='www/py-beautifulsoup32'
    export DEP_PY_LXML='devel/py-lxml'
fi

echo "* Detected Linux/BSD distribution: ${DISTRO}"
echo "* HTTP server root: ${HTTPD_SERVERROOT}"

restart_web_service()
{
    export web_service="${HTTPD_RC_SCRIPT_NAME}"
    if [ -f ${NGINX_PID_FILE} ]; then
        if [ -n "$(cat ${NGINX_PID_FILE})" ]; then
            export web_service="${UWSGI_RC_SCRIPT_NAME}"
        fi
    fi

    echo -n "* Restart service (${web_service}) to use new iRedAdmin release now? [Y|n] "
    read answer
    case $answer in
        n|N|no|NO )
            echo "* [SKIP] Please restart service ${HTTPD_RC_SCRIPT_NAME} or ${UWSGI_RC_SCRIPT_NAME} (if you're running Nginx as web server) manually."
            ;;
        y|Y|yes|YES|* )
            if [ X"${KERNEL_NAME}" == X'LINUX' -o X"${KERNEL_NAME}" == X'FREEBSD' ]; then
                service ${web_service} restart
            elif [ X"${KERNEL_NAME}" == X'OPENBSD' ]; then
                rcctl restart ${web_service}
            fi

            if [ X"$?" != X'0' ]; then
                echo "Failed, please restart service ${HTTPD_RC_SCRIPT_NAME} or ${UWSGI_RC_SCRIPT_NAME} (if you're running Nginx as web server) manually."
            fi
            ;;
    esac
}

install_pkg()
{
    echo "Install package: $@"

    if [ X"${DISTRO}" == X'RHEL' ]; then
        yum -y install $@
    elif [ X"${DISTRO}" == X'DEBIAN' -o X"${DISTRO}" == X'UBUNTU' ]; then
        apt-get install -y --force-yes $@
    elif [ X"${DISTRO}" == X'FREEBSD' ]; then
        cd /usr/ports/$@ && make install clean
    elif [ X"${DISTRO}" == X'OPENBSD' ]; then
        pkg_add -r $@
    else
        echo "<< ERROR >> Please install package(s) manually: $@"
    fi
}

add_missing_parameter()
{
    # Usage: add_missing_parameter VARIABLE DEFAULT_VALUE [COMMENT]
    var="${1}"
    value="${2}"
    shift 2
    comment="$@"

    if ! grep "^${var}" ${IRA_CONF_PY} &>/dev/null; then
        if [ ! -z "${comment}" ]; then
            echo "# ${comment}" >> ${IRA_CONF_PY}
        fi

        if [ X"${value}" == X'True' -o X"${value}" == X'False' ]; then
            echo "${var} = ${value}" >> ${IRA_CONF_PY}
        else
            # Value must be quoted as string.
            echo "${var} = '${value}'" >> ${IRA_CONF_PY}
        fi
    fi
}

has_python_module()
{
    mod="$1"
    python -c "import $mod" &>/dev/null
    if [ X"$?" == X'0' ]; then
        echo 'YES'
    else
        echo 'NO'
    fi
}

# iRedAdmin directory and config file.
export IRA_ROOT_DIR="${HTTPD_SERVERROOT}/iredadmin"
export IRA_CONF_PY="${IRA_ROOT_DIR}/settings.py"
export IRA_CONF_INI="${IRA_ROOT_DIR}/settings.ini"

if [ -L ${IRA_ROOT_DIR} ]; then
    export IRA_ROOT_REAL_DIR="$(readlink ${IRA_ROOT_DIR})"
    echo "* Found iRedAdmin directory: ${IRA_ROOT_DIR}, symbol link of ${IRA_ROOT_REAL_DIR}"
else
    echo "<<< ERROR >>> Directory is not a symbol link created by iRedMail. Exit."
    exit 255
fi

# Copy config file
if [ -f ${IRA_CONF_PY} ]; then
    echo "* Found iRedAdmin config file: ${IRA_CONF_PY}"
elif [ -f ${IRA_CONF_INI} ]; then
    echo "* Found iRedAdmin config file: ${IRA_CONF_INI}"
    echo "* Convert config file to new file name and format (settings.py)"
    cp ${IRA_CONF_INI} .
    bash convert_ini_to_py.sh settings.ini && \
        rm -f settings.ini && \
        mv settings.py ${IRA_CONF_PY} && \
        chmod 0400 ${IRA_CONF_PY}
else
    echo "<<< ERROR >>> Cannot find a valid config file (settings.py or settings.ini)."
    exit 255
fi

# Check whether current directory is iRedAdmin
PWD="$(pwd)"
if ! echo ${PWD} | grep 'iRedAdmin-.*/tools' >/dev/null; then
    echo "<<< ERROR >>> Cannot find new version of iRedAdmin in current directory. Exit."
    exit 255
fi

# Check whether it's iRedAdmin-Pro
IS_IRA_PRO='NO'
if echo ${PWD} | grep 'iRedAdmin-Pro-.*/tools' >/dev/null; then
    IS_IRA_PRO='YES'
fi

# Copy current directory to Apache server root
dir_new_version="$(dirname ${PWD})"
name_new_version="$(basename ${dir_new_version})"
NEW_IRA_ROOT_DIR="${HTTPD_SERVERROOT}/${name_new_version}"
if [ -d ${NEW_IRA_ROOT_DIR} ]; then
    COPY_FILES="${dir_new_version}/*"
    COPY_DEST_DIR="${NEW_IRA_ROOT_DIR}"
    #echo "<<< ERROR >>> Directory exist: ${NEW_IRA_ROOT_DIR}. Exit."
    #exit 255
else
    COPY_FILES="${dir_new_version}"
    COPY_DEST_DIR="${HTTPD_SERVERROOT}"
fi

echo "* Copying new version to ${NEW_IRA_ROOT_DIR}"
cp -rf ${COPY_FILES} ${COPY_DEST_DIR}

# Copy old config file
cp -p ${IRA_CONF_PY} ${NEW_IRA_ROOT_DIR}/
# Copy hooks.py. It's ok if missing.
cp -p ${IRA_ROOT_DIR}/hooks.py ${NEW_IRA_ROOT_DIR}/ &>/dev/null
# Copy custom files under 'tools/'. It's ok if missing.
cp -p ${IRA_ROOT_DIR}/tools/*.custom.* ${NEW_IRA_ROOT_DIR}/tools/ &>/dev/null
# Set owner and permission.
chown -R ${IRA_HTTPD_USER}:${IRA_HTTPD_GROUP} ${NEW_IRA_ROOT_DIR}
chmod -R 0555 ${NEW_IRA_ROOT_DIR}
chmod 0400 ${NEW_IRA_ROOT_DIR}/settings.py

echo "* Removing old symbol link ${IRA_ROOT_DIR}"
rm -f ${IRA_ROOT_DIR}

echo "* Creating symbol link ${IRA_ROOT_DIR} to ${NEW_IRA_ROOT_DIR}"
cd ${HTTPD_SERVERROOT}
ln -s ${name_new_version} iredadmin

# Delete all sessions to force admins to re-login.
cd ${NEW_IRA_ROOT_DIR}/tools/
python delete_sessions.py

# Add missing setting parameters.
if grep 'amavisd_enable_logging.*True.*' ${IRA_CONF_PY} &>/dev/null; then
    add_missing_parameter 'amavisd_enable_policy_lookup' True 'Enable per-recipient spam policy, white/blacklist.'
else
    add_missing_parameter 'amavisd_enable_policy_lookup' False 'Enable per-recipient spam policy, white/blacklist.'
fi

if ! grep '^iredapd_' ${IRA_CONF_PY} &>/dev/null; then
    add_missing_parameter 'iredapd_enabled' True 'Enable iRedAPD integration.'

    # Get iredapd db password from /opt/iredapd/settings.py.
    if [ -f /opt/iredapd/settings.py ]; then
        grep '^iredapd_db_' /opt/iredapd/settings.py >> ${IRA_CONF_PY}
        perl -pi -e 's#iredapd_db_server#iredapd_db_host#g' ${IRA_CONF_PY}
    else
        # Check backend.
        if egrep '^backend.*pgsql' ${IRA_CONF_PY} &>/dev/null; then
            export IREDAPD_DB_PORT='5432'
        else
            export IREDAPD_DB_PORT='3306'
        fi

        add_missing_parameter 'iredapd_db_host' '127.0.0.1'
        add_missing_parameter 'iredapd_db_port' ${IREDAPD_DB_PORT}
        add_missing_parameter 'iredapd_db_name' 'iredapd'
        add_missing_parameter 'iredapd_db_user' 'iredapd'
        add_missing_parameter 'iredapd_db_password' 'password'
    fi
fi
perl -pi -e 's#iredapd_db_server#iredapd_db_host#g' ${IRA_CONF_PY}

# Fix incorrect parameter name:
#   - ADDITION_USER_SERVICES -> ADDITIONAL_ENABLED_USER_SERVICES
perl -pi -e 's#ADDITION_USER_SERVICES#ADDITIONAL_ENABLED_USER_SERVICES#g' ${IRA_CONF_PY}

# Remove deprecated setting: ENABLE_SELF_SERVICE, it's now a per-domain setting.
perl -pi -e 's#^(ENABLE_SELF_SERVICE.*)##g' ${IRA_CONF_PY}

# Check dependent packages. Prompt to install missed ones manually.
echo "* Check and install dependent Python modules:"
echo "  + [required] json or simplejson"
if [ X"$(has_python_module json)" == X'NO' \
     -a X"$(has_python_module simplejson)" == X'NO' ]; then
    install_pkg $DEP_PY_JSON
fi
echo "  + [optional] BeautifulSoup"
if [ X"$(has_python_module bs4)" == X'NO' \
     -a X"$(has_python_module BeautifulSoup)" == X'NO' ]; then
    install_pkg $DEP_PY_BS4
fi

echo "  + [optional] lxml"
if [ X"$(has_python_module lxml)" == X'NO' ]; then
    install_pkg $DEP_PY_LXML
fi


#------------------------------
# Cron job.
#
[[ -d ${CRON_SPOOL_DIR} ]] || mkdir -p ${CRON_SPOOL_DIR} &>/dev/null
if [[ ! -f ${CRON_FILE} ]]; then
    touch ${CRON_FILE} &>/dev/null
    chmod 0600 ${CRON_FILE} &>/dev/null
fi

# cron job for cleaning up database.
if ! grep 'iredadmin/tools/cleanup_db.py' ${CRON_FILE} &>/dev/null; then
    cat >> ${CRON_FILE} <<EOF
# iRedAdmin: Clean up sql database.
1   *   *   *   *   ${PYTHON_BIN} ${IRA_ROOT_DIR}/tools/cleanup_db.py &>/dev/null
EOF
fi


echo "* iRedAdmin was successfully upgraded, restarting web service is required."
restart_web_service

# Clean up.
cd ${NEW_IRA_ROOT_DIR}/
rm -f settings.pyc settings.pyo tools/settings.py

echo "* Upgrading completed."

cat <<EOF
<<< NOTE >>> If iRedAdmin doesn't work as expected, please post your issue in
<<< NOTE >>> our online support forum: http://www.iredmail.org/forum/
EOF
