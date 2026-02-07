FROM debian:bookworm-slim

ARG PROTOC_VERSION=27.3
ARG BUF_VERSION=1.47.2
ARG DART_SDK_VERSION=3.5.4

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    gnupg \
    python3 \
    python3-pip \
    unzip \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

# Install protoc
RUN curl -fsSL -o /tmp/protoc.zip \
    "https://github.com/protocolbuffers/protobuf/releases/download/v${PROTOC_VERSION}/protoc-${PROTOC_VERSION}-linux-x86_64.zip" \
    && unzip /tmp/protoc.zip -d /usr/local \
    && rm /tmp/protoc.zip

# Install buf
RUN curl -fsSL -o /usr/local/bin/buf \
    "https://github.com/bufbuild/buf/releases/download/v${BUF_VERSION}/buf-Linux-x86_64" \
    && chmod +x /usr/local/bin/buf

# Install Python protobuf plugins
RUN python3 -m pip install --no-cache-dir \
    grpcio-tools==1.68.0 \
    mypy-protobuf==3.6.0

# Install Dart SDK + protoc plugin
RUN curl -fsSL -o /tmp/dart.zip \
    "https://storage.googleapis.com/dart-archive/channels/stable/release/${DART_SDK_VERSION}/sdk/dartsdk-linux-x64-release.zip" \
    && unzip /tmp/dart.zip -d /usr/local \
    && rm /tmp/dart.zip

ENV PATH="/usr/local/dart-sdk/bin:/root/.pub-cache/bin:${PATH}"
RUN dart --disable-analytics \
    && dart pub global activate protoc_plugin 22.3.0

WORKDIR /workspace

ENTRYPOINT ["/bin/bash", "-lc"]
