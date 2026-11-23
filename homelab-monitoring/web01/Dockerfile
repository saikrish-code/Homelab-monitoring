FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      nginx nagios-nrpe-server monitoring-plugins-basic supervisor \
      stress-ng procps util-linux curl iputils-ping \
 && rm -rf /var/lib/apt/lists/* \
 && rm -f /etc/nginx/sites-enabled/default \
 && mkdir -p /data && chmod 1777 /data

COPY nginx-lab.conf /etc/nginx/conf.d/lab.conf
COPY index.html /var/www/html/index.html
COPY nrpe.cfg /etc/nagios/nrpe.cfg
COPY supervisord.conf /etc/supervisord-lab.conf
RUN nginx -t

EXPOSE 80 5666
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisord-lab.conf"]
