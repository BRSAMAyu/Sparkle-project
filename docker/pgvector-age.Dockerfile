FROM pgvector/pgvector:pg16

ARG AGE_REF=PG16/v1.6.0-rc0

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    flex \
    bison \
    git \
    libreadline-dev \
    zlib1g-dev \
    postgresql-server-dev-16 \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --branch "${AGE_REF}" --depth 1 https://github.com/apache/age.git /tmp/age \
    && make -C /tmp/age PG_CONFIG=/usr/bin/pg_config install \
    && rm -rf /tmp/age
