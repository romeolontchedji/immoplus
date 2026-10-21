# Une seule image, plusieurs commandes (web-api, realtime, admin, worker, worker-media, beat, migrer).
# Pas de Node : le CSS est assemblé par un script Python (outils/construire_css.py).
FROM python:3.12-slim-bookworm AS construction
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /construction
COPY serveur/requirements/base.txt requirements.txt
RUN python -m venv /venv && /venv/bin/pip install --require-virtualenv -r requirements.txt

FROM python:3.12-slim-bookworm AS execution
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PATH="/venv/bin:$PATH" PYTHONPATH=/app
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg libpq5 libheif1 tini curl \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system --gid 10001 immoplus \
 && useradd --system --uid 10001 --gid immoplus --home-dir /app --shell /usr/sbin/nologin immoplus \
 && mkdir -p /app /var/lib/immoplus/static /var/lib/immoplus/media_tmp /var/lib/immoplus/media_public /var/lib/immoplus/media_private \
 && chown -R immoplus:immoplus /app /var/lib/immoplus
COPY --from=construction /venv /venv
WORKDIR /app
COPY --chown=immoplus:immoplus serveur/ /app/
COPY outils/construire_css.py /opt/outils/construire_css.py
RUN IMMOPLUS_CSS_SOURCES=/app/web/static/css python /opt/outils/construire_css.py
COPY --chown=immoplus:immoplus infra/docker/entrypoint.sh /entrypoint.sh
RUN chmod 0755 /entrypoint.sh && chown -R immoplus:immoplus /app/web/static
USER immoplus
EXPOSE 8000 8001 8002
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT:-8000}/healthz" || exit 1
ENTRYPOINT ["/usr/bin/tini", "--", "/entrypoint.sh"]
CMD ["web-api"]
