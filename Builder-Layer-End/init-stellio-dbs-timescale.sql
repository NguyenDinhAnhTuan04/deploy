-- Initialize Stellio databases with TimescaleDB extension
-- Stellio requires TimescaleDB for time-series data hypertables

-- Create databases for Stellio services
CREATE DATABASE stellio_search;
CREATE DATABASE stellio_subscription;

-- Connect to stellio_search and enable TimescaleDB + PostGIS
\c stellio_search
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS postgis;

-- Connect to stellio_subscription and enable TimescaleDB + PostGIS  
\c stellio_subscription
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS postgis;
