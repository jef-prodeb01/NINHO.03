-- =============================================================================
-- NINHO — 01_create_tablespaces.sql (PROJETO: GLD)
-- =============================================================================
CREATE TABLESPACE GLD_DATA DATAFILE 'gld_data01.dbf' SIZE 500M AUTOEXTEND ON NEXT 100M MAXSIZE UNLIMITED;
CREATE TABLESPACE GLD_INDEX DATAFILE 'gld_index01.dbf' SIZE 250M AUTOEXTEND ON NEXT 50M MAXSIZE UNLIMITED;
