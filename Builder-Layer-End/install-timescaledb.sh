#!/bin/bash
# Install TimescaleDB extension in PostGIS image
set -e

# Add TimescaleDB repository
echo "deb https://packagecloud.io/timescale/timescaledb/debian/ $(lsb_release -c -s) main" > /etc/apt/sources.list.d/timescaledb.list
wget --quiet -O - https://packagecloud.io/timescale/timescaledb/gpgkey | apt-key add -

# Update and install TimescaleDB
apt-get update
apt-get install -y timescaledb-2-postgresql-15
