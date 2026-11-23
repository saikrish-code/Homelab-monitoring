FROM mariadb:10.11

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      nagios-nrpe-server monitoring-plugins-basic supervisor procps stress-ng \
 && rm -rf /var/lib/apt/lists/*

COPY nrpe.cfg /etc/nagios/nrpe.cfg
COPY supervisord.conf /etc/supervisord-lab.conf
COPY init/ /docker-entrypoint-initdb.d/
RUN chmod 755 /docker-entrypoint-initdb.d/*.sh

EXPOSE 3306 5666
ENTRYPOINT ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisord-lab.conf"]
CMD []
