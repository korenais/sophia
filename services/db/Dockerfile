FROM postgres:15

COPY init.sql /docker-entrypoint-initdb.d/001-init.sql
COPY migrate_to_latest.sql /docker-entrypoint-initdb.d/002-migrate_to_latest.sql
