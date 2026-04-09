-- ============================================
-- PostgreSQL Initialization Script
-- Auto-generated for DocuLogic
-- ============================================

-- 设置客户端编码
SET client_encoding = 'UTF8';

-- 删除已存在的表（按依赖顺序）
DROP TABLE IF EXISTS app_settings CASCADE;
DROP TABLE IF EXISTS parse_jobs CASCADE;
DROP TABLE IF EXISTS verification_codes CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- 创建用户表
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    username TEXT NOT NULL UNIQUE,
    hashed_password TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    failed_login_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_admin BOOLEAN DEFAULT FALSE,
    phone TEXT,
    pdf_max_pages INTEGER,
    can_download_images BOOLEAN DEFAULT TRUE,
    image_output_mode TEXT DEFAULT 'base64'
);

-- 创建验证码表
CREATE TABLE verification_codes (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    code_hash TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    purpose TEXT DEFAULT 'register'
);

-- 创建解析任务表
CREATE TABLE parse_jobs (
    job_id UUID PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'processing',
    original_filename TEXT,
    completed_at TIMESTAMP,
    cache_cleared_at TIMESTAMP,
    pages_parsed INTEGER
);

-- 创建系统配置表
CREATE TABLE app_settings (
    id INTEGER PRIMARY KEY DEFAULT 1,
    registration_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    captcha_login_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    captcha_register_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    captcha_forgot_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    pdf_max_pages INTEGER NOT NULL DEFAULT 80,
    output_dir TEXT,
    model_local_path TEXT,
    hf_repo_id TEXT NOT NULL DEFAULT 'Logics-MLLM/Logics-Parsing-v2',
    ms_repo_id TEXT NOT NULL DEFAULT 'Alibaba-DT/Logics-Parsing-v2',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    email_mock BOOLEAN DEFAULT TRUE,
    smtp_host TEXT,
    smtp_port INTEGER DEFAULT 587,
    smtp_user TEXT,
    smtp_password TEXT,
    smtp_from TEXT,
    smtp_use_tls BOOLEAN DEFAULT TRUE,
    register_email_enabled BOOLEAN DEFAULT TRUE,
    register_phone_enabled BOOLEAN DEFAULT TRUE,
    login_email_enabled BOOLEAN DEFAULT TRUE,
    login_phone_enabled BOOLEAN DEFAULT TRUE,
    forgot_email_enabled BOOLEAN DEFAULT TRUE,
    forgot_phone_enabled BOOLEAN DEFAULT TRUE,
    sms_mock BOOLEAN DEFAULT TRUE,
    sms_http_url TEXT,
    sms_http_secret TEXT,
    sms_http_headers_json TEXT,
    sms_http_body_template TEXT,
    show_page_numbers BOOLEAN DEFAULT TRUE,
    image_output_mode TEXT DEFAULT 'base64',
    stale_job_timeout_minutes INTEGER NOT NULL DEFAULT 10,
    login_timeout_minutes INTEGER DEFAULT 10,
    password_min_length INTEGER DEFAULT 8,
    password_require_uppercase BOOLEAN DEFAULT TRUE,
    password_require_lowercase BOOLEAN DEFAULT TRUE,
    password_require_digit BOOLEAN DEFAULT TRUE,
    password_require_special BOOLEAN DEFAULT FALSE,
    max_upload_size_mb INTEGER DEFAULT 50,
    allow_multi_file_upload BOOLEAN DEFAULT TRUE
);

-- 插入默认管理员账号（密码: admin123）
-- 注意：实际部署时应修改此密码
INSERT INTO users (id, email, username, hashed_password, is_active, is_admin, created_at) 
VALUES (
    1,
    'admin@logics-parsing.local',
    'admin',
    '$2b$12$I0VJKvfMeRGtLYWXr0pRZObYDNgovHCKbcQa3koDVSOpQazGF6J0u',
    TRUE,
    TRUE,
    CURRENT_TIMESTAMP
);

-- 插入默认系统配置
INSERT INTO app_settings (
    id,
    registration_enabled,
    captcha_login_enabled,
    captcha_register_enabled,
    captcha_forgot_enabled,
    pdf_max_pages,
    hf_repo_id,
    ms_repo_id,
    updated_at,
    email_mock,
    smtp_port,
    smtp_use_tls,
    register_email_enabled,
    register_phone_enabled,
    login_email_enabled,
    login_phone_enabled,
    forgot_email_enabled,
    forgot_phone_enabled,
    sms_mock,
    show_page_numbers,
    image_output_mode,
    stale_job_timeout_minutes,
    login_timeout_minutes,
    password_min_length,
    password_require_uppercase,
    password_require_lowercase,
    password_require_digit,
    password_require_special,
    max_upload_size_mb,
    allow_multi_file_upload
) VALUES (
    1,
    TRUE,   -- registration_enabled
    FALSE,  -- captcha_login_enabled
    FALSE,  -- captcha_register_enabled
    FALSE,  -- captcha_forgot_enabled
    80,     -- pdf_max_pages
    'Logics-MLLM/Logics-Parsing-v2',  -- hf_repo_id
    'Alibaba-DT/Logics-Parsing-v2',   -- ms_repo_id
    CURRENT_TIMESTAMP,  -- updated_at
    TRUE,   -- email_mock
    587,    -- smtp_port
    TRUE,   -- smtp_use_tls
    TRUE,   -- register_email_enabled
    TRUE,   -- register_phone_enabled
    TRUE,   -- login_email_enabled
    TRUE,   -- login_phone_enabled
    TRUE,   -- forgot_email_enabled
    TRUE,   -- forgot_phone_enabled
    TRUE,   -- sms_mock
    TRUE,   -- show_page_numbers
    'base64',  -- image_output_mode
    10,     -- stale_job_timeout_minutes
    10,     -- login_timeout_minutes
    8,      -- password_min_length
    TRUE,   -- password_require_uppercase
    TRUE,   -- password_require_lowercase
    TRUE,   -- password_require_digit
    FALSE,  -- password_require_special
    50,     -- max_upload_size_mb
    TRUE    -- allow_multi_file_upload
);

-- 创建索引以提高查询性能
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_parse_jobs_user_id ON parse_jobs(user_id);
CREATE INDEX idx_parse_jobs_status ON parse_jobs(status);
CREATE INDEX idx_verification_codes_email ON verification_codes(email);
CREATE INDEX idx_verification_codes_expires_at ON verification_codes(expires_at);
