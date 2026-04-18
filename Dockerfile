FROM ghcr.io/hydropix/translatebookswithllms:latest

RUN apt-get update -qq \
  && apt-get install -y --no-install-recommends ffmpeg \
  && rm -rf /var/lib/apt/lists/*

COPY . /app