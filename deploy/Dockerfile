FROM python:3.11-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates gcc \
    && rm -rf /var/lib/apt/lists/*

# v2026.8.19 is Hermes 0.20.5. A later snapshot only publishes wheels for Python 3.14.
ARG HERMES_COMMIT=fcbd1076a93841fa88855acce810e342a5b78101
RUN git init /opt/hermes \
    && git -C /opt/hermes remote add origin https://github.com/NousResearch/hermes-agent.git \
    && git -C /opt/hermes fetch --depth 1 origin "$HERMES_COMMIT" \
    && git -C /opt/hermes checkout --detach FETCH_HEAD
# setup.py blocks wheel builds and also drops the dependency list, so install
# the declared requirements first and then link the checkout with --no-deps.
RUN python -c "import tomllib; from pathlib import Path; data=tomllib.loads(Path('/opt/hermes/pyproject.toml').read_text(encoding='utf-8')); reqs=list(data['project']['dependencies'])+list(data['project']['optional-dependencies']['messaging']); Path('/tmp/hermes-reqs.txt').write_text('\n'.join(reqs)+'\n', encoding='utf-8')" \
    && pip install --no-cache-dir -r /tmp/hermes-reqs.txt \
    && pip install --no-cache-dir --no-deps -e /opt/hermes \
    && rm /tmp/hermes-reqs.txt \
    && apt-get update \
    && apt-get purge -y gcc \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* /root/.cache

COPY --from=docker.io/tailscale/tailscale:stable /usr/local/bin/tailscaled /usr/local/bin/tailscaled
COPY --from=docker.io/tailscale/tailscale:stable /usr/local/bin/tailscale /usr/local/bin/tailscale
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin lumen
COPY deploy/isolation-report.sh /usr/local/bin/isolation-report.sh
COPY deploy/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY deploy/ollama_forward.py deploy/route_check.py deploy/openai_proxy.py deploy/install_cloud_jobs.py deploy/continuity.py /opt/lumen/
COPY router /opt/lumen/app/router
COPY lib /opt/lumen/app/lib
COPY cron /opt/lumen/app/cron
COPY skills /opt/lumen/app/skills
COPY synthetic /opt/lumen/app/synthetic
COPY hermes/SOUL.md hermes/USER.md /opt/lumen/seed/
RUN chmod 755 /usr/local/bin/isolation-report.sh /usr/local/bin/entrypoint.sh \
    && chown -R lumen:lumen /opt/lumen

USER lumen
ENV HERMES_HOME=/hermes \
    HOME=/home/lumen \
    LUMEN_APP=/opt/lumen/app \
    API_SERVER_HOST=0.0.0.0 \
    API_SERVER_PORT=8080 \
    PYTHONUNBUFFERED=1
WORKDIR /home/lumen
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
