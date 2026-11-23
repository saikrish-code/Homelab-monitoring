FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      nagios4 monitoring-plugins nagios-nrpe-plugin libmysqlclient21 \
      apache2 apache2-utils supervisor \
      python3 python3-requests iputils-ping curl ca-certificates procps \
 && rm -rf /var/lib/apt/lists/*

# Replace the packaged (digest-auth) Apache config with our simple basic-auth one
RUN rm -f /etc/apache2/conf-enabled/nagios4*.conf \
 && a2enmod cgi alias auth_basic authn_file authz_user >/dev/null

COPY nagios/apache-lab.conf /etc/apache2/conf-available/lab-nagios.conf
RUN a2enconf lab-nagios >/dev/null

# Nagios configuration (own nagios.cfg + objects)
COPY nagios/nagios.cfg /etc/nagios4/nagios.cfg
COPY nagios/lab/ /etc/nagios4/lab/

# Custom plugin + integration scripts
COPY nagios/plugins/check_json_status.py /usr/lib/nagios/plugins/check_json_status.py
COPY integration/ /opt/lab/
RUN chmod 755 /usr/lib/nagios/plugins/check_json_status.py /opt/lab/*.py

COPY nagios/supervisord.conf /etc/supervisord-lab.conf
COPY nagios/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 755 /usr/local/bin/entrypoint.sh

# Fail the build early if the Nagios config is invalid
RUN mkdir -p /var/lib/nagios4/spool/checkresults /var/cache/nagios4 /var/log/nagios4 \
 && /usr/sbin/nagios4 -v /etc/nagios4/nagios.cfg

EXPOSE 80
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
