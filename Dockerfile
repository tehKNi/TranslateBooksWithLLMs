ARG BASE_IMAGE=ghcr.io/tehkni/translatebookswithllms:latest
FROM ${BASE_IMAGE}

ARG INSTALL_CHATTERBOX=0
ARG INSTALL_OMNIVOICE=0

RUN apt-get update -qq \
  && apt-get install -y --no-install-recommends ffmpeg \
  && if [ "$INSTALL_CHATTERBOX" = "1" ] || [ "$INSTALL_CHATTERBOX" = "true" ]; then python -m pip install --no-cache-dir torch torchaudio chatterbox-tts; fi \
  && if [ "$INSTALL_OMNIVOICE" = "1" ] || [ "$INSTALL_OMNIVOICE" = "true" ]; then python -m pip install --no-cache-dir torch torchaudio omnivoice; fi \
  && rm -rf /var/lib/apt/lists/*

COPY . /app
