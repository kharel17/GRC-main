-- Create application role
CREATE USER grc_app_user WITH PASSWORD 'grc_app_secret';

-- Grant database & schema access
GRANT CONNECT ON DATABASE grc_db TO grc_app_user;
GRANT USAGE ON SCHEMA public TO grc_app_user;

-- Grant standard CRUD privileges on existing and future tables
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO grc_app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO grc_app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO grc_app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO grc_app_user;
