-- database schema to load into DB for the very first time the container is created
-- this approach generated an error which turned tricky to fix - use manual option

-- =========================
-- Reference Tables
-- =========================

-- commented out, created "code-first" as required for custom user model
-- CREATE TABLE roles (
--     id SERIAL PRIMARY KEY,
--     name VARCHAR(50) UNIQUE NOT NULL,
--     description TEXT
-- );

-- commented out, created "code-first" as required for custom user model
-- CREATE TABLE business_units (
--     id SERIAL PRIMARY KEY,
--     name VARCHAR(255) NOT NULL,
--     parent_id INT REFERENCES business_units(id) ON DELETE SET NULL
-- );



-- =========================
-- Core Tables
-- =========================

-- commented out, created "code-first" as required for custom user model
-- CREATE TABLE users (
--     id SERIAL PRIMARY KEY,
--     username VARCHAR(100) UNIQUE NOT NULL,
--     email VARCHAR(255) UNIQUE NOT NULL, -- consider it for login + psw
--     full_name VARCHAR(255),
--     business_unit_id INT REFERENCES business_units(id) ON DELETE SET NULL,
--     role_id INT REFERENCES roles(id) ON DELETE SET NULL,
--     manager_id INT NULL REFERENCES users(id), -- required for incid. routing/transitions
--     external_id VARCHAR(255) NULL, -- ready for AD sync
--     external_source VARCHAR(50) NULL, -- ready for AD sync
--     is_active BOOLEAN NOT NULL DEFAULT TRUE,
--     created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
-- );