FROM ghcr.io/hydropix/translatebookswithllms:latest

ARG INSTALL_CHATTERBOX=0

RUN apt-get update -qq \
  && apt-get install -y --no-install-recommends ffmpeg \
  && if [ "$INSTALL_CHATTERBOX" = "1" ] || [ "$INSTALL_CHATTERBOX" = "true" ]; then python -m pip install --no-cache-dir torch torchaudio chatterbox-tts; fi \
  && rm -rf /var/lib/apt/lists/*

COPY . /app
