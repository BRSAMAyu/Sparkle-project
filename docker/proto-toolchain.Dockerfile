FROM debian:bookworm-slim

ARG PROTOC_VERSION=27.3
ARG BUF_VERSION=1.47.2
# WT280: protoc_plugin 25.1.0 的 pubspec 约束是 sdk >=3.7.0 <4.0.0，Dart 3.6.1 会使
# 本镜像构建失败并堵死整条 CI（lint 首步即 make proto-tools-build）。配对三元组:
# Dart >=3.7.0 ↔ protoc_plugin 25.1.0 ↔ protobuf 6.1.0（mobile 运行时锁定）。
ARG DART_SDK_VERSION=3.7.2

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
# --break-system-packages: required by PEP 668 on bookworm's system Python
RUN python3 -m pip install --no-cache-dir --break-system-packages \
    grpcio-tools==1.68.0 \
    mypy-protobuf==3.6.0

# Install Dart SDK + protoc plugin
RUN curl -fsSL -o /tmp/dart.zip \
    "https://storage.googleapis.com/dart-archive/channels/stable/release/${DART_SDK_VERSION}/sdk/dartsdk-linux-x64-release.zip" \
    && unzip /tmp/dart.zip -d /usr/local \
    && rm /tmp/dart.zip

ENV PATH="/usr/local/dart-sdk/bin:/root/.pub-cache/bin:${PATH}"
# protoc_plugin 25.1.0 与 mobile 锁定的 protobuf 6.1.0 运行时配对（22.x 产物需 ^4.x 运行时，编译必断）
RUN dart --disable-analytics \
    && dart pub global activate protoc_plugin 25.1.0 \
    && ln -sf /usr/local/dart-sdk/bin/dart /usr/local/bin/dart \
    && ln -sf /root/.pub-cache/bin/protoc-gen-dart /usr/local/bin/protoc-gen-dart

WORKDIR /workspace

ENTRYPOINT ["/bin/bash", "-lc"]
