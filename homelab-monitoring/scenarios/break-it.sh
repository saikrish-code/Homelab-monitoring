#!/usr/bin/env bash
# Outage simulator.  Usage: ./scenarios/break-it.sh <scenario>
set -euo pipefail
NET="homelab_labnet"
SCTL="supervisorctl -c /etc/supervisord-lab.conf"

usage() {
cat <<EOF
Break:                         Fix:
  web-down                       web-up
  nginx-crash                    nginx-fix
  bad-config                     bad-config-fix
  db-crash                       db-fix
  disk-fill                      disk-fix
  cpu-load                       cpu-fix
  net-cut                        net-fix
  all-fixed   (undo everything)
EOF
}

case "${1:-}" in
  web-down)       docker stop web01 ;;
  web-up)         docker start web01 ;;
  nginx-crash)    docker exec web01 pkill nginx || true ;;
  nginx-fix)      docker exec web01 $SCTL start nginx ;;
  bad-config)     docker exec web01 sh -c 'echo "this is not valid nginx config;" > /etc/nginx/conf.d/broken.conf'
                  docker exec web01 pkill nginx || true
                  docker exec web01 $SCTL start nginx || true ;;
  bad-config-fix) docker exec web01 rm -f /etc/nginx/conf.d/broken.conf
                  docker exec web01 $SCTL start nginx ;;
  db-crash)       docker exec db01 pkill -9 mariadbd || true ;;
  db-fix)         docker exec db01 $SCTL start mariadb ;;
  disk-fill)      docker exec web01 fallocate -l 95M /data/fill.bin ;;
  disk-fix)       docker exec web01 rm -f /data/fill.bin ;;
  cpu-load)       docker exec -d web01 sh -c 'stress-ng --cpu $(( $(nproc) * 3 )) --timeout 600s' ;;
  cpu-fix)        docker exec web01 pkill stress-ng || true ;;
  net-cut)        docker network disconnect "$NET" web01 ;;
  net-fix)        docker network connect --ip 172.20.0.11 "$NET" web01 ;;
  all-fixed)
    "$0" net-fix  2>/dev/null || true
    "$0" web-up   2>/dev/null || true
    "$0" cpu-fix  2>/dev/null || true
    "$0" disk-fix 2>/dev/null || true
    "$0" bad-config-fix 2>/dev/null || true
    "$0" nginx-fix 2>/dev/null || true
    "$0" db-fix   2>/dev/null || true ;;
  *) usage; exit 1 ;;
esac
echo "done: ${1:-}"
