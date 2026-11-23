#!/usr/bin/env bash
set -euo pipefail

: "${NAGIOSADMIN_PASS:?NAGIOSADMIN_PASS is required}"
: "${NAGIOS_DB_PASS:?NAGIOS_DB_PASS is required}"

# Secrets are injected at runtime, never baked into the image
printf '$USER1$=/usr/lib/nagios/plugins\n$USER2$=%s\n' "$NAGIOS_DB_PASS" > /etc/nagios4/resource.cfg
chown root:nagios /etc/nagios4/resource.cfg
chmod 640 /etc/nagios4/resource.cfg

htpasswd -bc /etc/nagios4/htpasswd.users nagiosadmin "$NAGIOSADMIN_PASS" >/dev/null 2>&1
chown root:www-data /etc/nagios4/htpasswd.users
chmod 640 /etc/nagios4/htpasswd.users

# Runtime directories
mkdir -p /var/lib/nagios4/rw /var/lib/nagios4/spool/checkresults /var/cache/nagios4 \
         /var/log/nagios4/archives /var/run/apache2 /var/lock/apache2
chown -R nagios:nagios /var/lib/nagios4 /var/cache/nagios4 /var/log/nagios4
chown nagios:www-data /var/lib/nagios4/rw
chmod 2710 /var/lib/nagios4/rw
chmod 755 /var/log/nagios4 /var/cache/nagios4

echo "[entrypoint] validating Nagios configuration..."
/usr/sbin/nagios4 -v /etc/nagios4/nagios.cfg | tail -n 12

if [ -z "${SNOW_INSTANCE:-}" ]; then
  echo "[entrypoint] SNOW_INSTANCE not set -> ServiceNow bridge runs in DRY-RUN mode (log only)"
else
  echo "[entrypoint] ServiceNow bridge enabled for instance: ${SNOW_INSTANCE}"
fi

exec /usr/bin/supervisord -n -c /etc/supervisord-lab.conf
