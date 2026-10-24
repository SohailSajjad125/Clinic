-- Least-privilege database setup. Run once as a PostgreSQL admin, replacing the two passwords.
-- clinicos_owner  : owns the schema, runs migrations (alembic). Never used by the running API.
-- clinicos_app    : used by the running API. Can read and write rows only: no DDL, no superuser, cannot create databases or roles.
CREATE ROLE clinicos_owner LOGIN PASSWORD 'REPLACE_WITH_LONG_RANDOM_PASSWORD' NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE clinicos_app   LOGIN PASSWORD 'REPLACE_WITH_ANOTHER_LONG_RANDOM_PASSWORD' NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE DATABASE clinicos OWNER clinicos_owner;
\connect clinicos
REVOKE ALL ON DATABASE clinicos FROM PUBLIC;
GRANT CONNECT ON DATABASE clinicos TO clinicos_app;
GRANT USAGE ON SCHEMA public TO clinicos_app;
ALTER DEFAULT PRIVILEGES FOR ROLE clinicos_owner IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO clinicos_app;
ALTER DEFAULT PRIVILEGES FOR ROLE clinicos_owner IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO clinicos_app;
-- Migrations:  DATABASE_URL=postgresql+psycopg://clinicos_owner:...@host/clinicos?sslmode=require  alembic upgrade head
-- Running API: DATABASE_URL=postgresql+psycopg://clinicos_app:...@host/clinicos?sslmode=require
