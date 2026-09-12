FROM python:3.11-slim

# libgraphite2-3 is tectonic's one genuine runtime shared-lib dependency
# beyond what this base image already provides (confirmed via `ldd` against
# the installed binary -- everything else it links against, e.g. harfbuzz
# and openssl, is statically vendored).
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates libgraphite2-3 \
    && rm -rf /var/lib/apt/lists/*

# Install tectonic via its official standalone installer script.
# Verified working (built + smoke-tested a real .tex -> PDF compile) as of
# tectonic's installer at https://drop-sh.fullyjustified.net.
WORKDIR /tmp/tectonic-install
RUN curl --proto '=https' --tlsv1.2 -fsSL https://drop-sh.fullyjustified.net | sh \
    && mv tectonic /usr/local/bin/tectonic \
    && chmod +x /usr/local/bin/tectonic \
    && cd / && rm -rf /tmp/tectonic-install

RUN useradd --create-home --shell /usr/sbin/nologin appuser
# Pre-create the cache dir with correct ownership so that when the
# tectonic-cache named volume is first mounted here, Docker copies this
# directory's (appuser-owned) permissions into the volume instead of
# defaulting the mount point to root.
RUN mkdir -p /home/appuser/.cache && chown -R appuser:appuser /home/appuser/.cache

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
RUN chown -R appuser:appuser /app

USER appuser
ENV HOME=/home/appuser

# Pre-warm tectonic's package cache + generated format file at build time.
# tectonic's very first-ever compile builds the base LaTeX format, which
# fetches hyphenation patterns for every babel language one file at a time
# (several minutes over the network). Baking that into the image here means
# a fresh container/volume never has to pay that cost at request time --
# Docker copies this pre-populated ~/.cache into the tectonic-cache volume
# the first time it's mounted (same mechanism as the ownership fix above).
RUN mkdir -p /tmp/warmup/out && cd /tmp/warmup \
    && printf '\\documentclass{article}\\begin{document}warmup\\end{document}' > warmup.tex \
    && tectonic warmup.tex --outdir /tmp/warmup/out \
    && rm -rf /tmp/warmup

EXPOSE 8100
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8100"]
