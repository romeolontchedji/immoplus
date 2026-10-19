#!/bin/sh
# Point d'entrée unique : le premier argument choisit le processus.
set -eu

cmd="${1:-web-api}"
[ "$#" -gt 0 ] && shift
export LOGEO_SERVICE="$cmd"  # nom du processus, repris par le suivi des erreurs
reload=""
[ "${LOGEO_RELOAD:-0}" = "1" ] && reload="--reload"

case "$cmd" in
  web-api)
    PORT=8000
    exec gunicorn config.asgi:application -k uvicorn_worker.UvicornWorker \
      -b 0.0.0.0:8000 -w "${WEB_CONCURRENCY:-2}" --max-requests 1000 --max-requests-jitter 100 \
      --graceful-timeout 30 --access-logfile - $reload ;;
  realtime)
    exec gunicorn config.asgi:application -k uvicorn_worker.UvicornWorker \
      -b 0.0.0.0:8001 -w "${WEB_CONCURRENCY:-1}" --timeout 0 --graceful-timeout 30 $reload ;;
  admin)
    exec gunicorn config.asgi:application -k uvicorn_worker.UvicornWorker \
      -b 0.0.0.0:8002 -w 1 --graceful-timeout 30 $reload ;;
  worker)
    exec celery -A config.celery worker -Q default,notifications -c "${CELERY_CONCURRENCY:-4}" -l info ;;
  worker-media)
    exec celery -A config.celery worker -Q media -c 1 --max-tasks-per-child 20 -l info ;;
  beat)
    exec python -m config.beat_unique ;;
  migrer)
    python manage.py migrate --noinput
    exec python manage.py collectstatic --noinput ;;
  *)
    exec "$cmd" "$@" ;;
esac
