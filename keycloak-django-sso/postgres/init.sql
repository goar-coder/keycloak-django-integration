-- Create dedicated users for each service
CREATE USER keycloak_user WITH PASSWORD 'keycloak_pass';
CREATE USER d1_user WITH PASSWORD 'd1_pass' CREATEDB;
CREATE USER d2_user WITH PASSWORD 'd2_pass' CREATEDB;

-- Create isolated databases
CREATE DATABASE keycloak_db OWNER keycloak_user;
CREATE DATABASE d1_db OWNER d1_user;
CREATE DATABASE d2_db OWNER d2_user;

-- Revoke default public access
REVOKE ALL ON DATABASE keycloak_db FROM PUBLIC;
REVOKE ALL ON DATABASE d1_db FROM PUBLIC;
REVOKE ALL ON DATABASE d2_db FROM PUBLIC;

-- Grant privileges to each owner only
GRANT ALL PRIVILEGES ON DATABASE keycloak_db TO keycloak_user;
GRANT ALL PRIVILEGES ON DATABASE d1_db TO d1_user;
GRANT ALL PRIVILEGES ON DATABASE d2_db TO d2_user;
