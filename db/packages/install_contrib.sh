# #!/bin/bash

# # Compilation of PostgreSQL
# apt-get update \
#     && apt-get install -y curl uuid-dev
# curl --progress-bar https://ftp.postgresql.org/pub/source/v${PG_VERSION}/postgresql-${PG_VERSION}.tar.bz2 | tar xj -C /usr/local/src/
# cd src/postgresql-${PG_VERSION}/contrib
#     make -j "$(nproc)"
#     make install
#     make all
#     make install
# cd ../../..
# ldconfig
# # Clean up
# rm -rf /usr/local/src