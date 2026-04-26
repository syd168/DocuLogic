-- ============================================
-- MariaDB Initialization Script
-- Auto-generated for DocuLogic
-- Compatible with MariaDB 10.5+
-- ============================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- 表: users
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `email` LONGTEXT NOT NULL,
  `username` VARCHAR(255) NOT NULL,
  `hashed_password` LONGTEXT NOT NULL,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `failed_login_attempts` INT NOT NULL DEFAULT 0,
  `locked_until` DATETIME,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `is_admin` TINYINT(1) DEFAULT 0,
  `phone` LONGTEXT,
  `pdf_max_pages` INT,
  `can_download_images` TINYINT(1) DEFAULT 1,
  `image_output_mode` LONGTEXT DEFAULT 'base64',
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_users_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 表: verification_codes
DROP TABLE IF EXISTS `verification_codes`;
CREATE TABLE `verification_codes` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `email` LONGTEXT NOT NULL,
  `code_hash` LONGTEXT NOT NULL,
  `expires_at` DATETIME NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `purpose` LONGTEXT DEFAULT 'register',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 表: parse_jobs
DROP TABLE IF EXISTS `parse_jobs`;
CREATE TABLE `parse_jobs` (
  `job_id` VARCHAR(36) NOT NULL,
  `user_id` INT NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `status` LONGTEXT DEFAULT 'processing',
  `original_filename` LONGTEXT,
  `completed_at` DATETIME,
  `cache_cleared_at` DATETIME,
  `pages_parsed` INT,
  PRIMARY KEY (`job_id`),
  CONSTRAINT `fk_parse_jobs_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 表: app_settings
DROP TABLE IF EXISTS `app_settings`;
CREATE TABLE `app_settings` (
  `id` INT NOT NULL DEFAULT 1,
  `registration_enabled` TINYINT(1) NOT NULL DEFAULT 1,
  `captcha_login_enabled` TINYINT(1) NOT NULL DEFAULT 0,
  `captcha_register_enabled` TINYINT(1) NOT NULL DEFAULT 0,
  `captcha_forgot_enabled` TINYINT(1) NOT NULL DEFAULT 0,
  `pdf_max_pages` INT NOT NULL DEFAULT 80,
  `output_dir` LONGTEXT,
  `model_local_path` LONGTEXT,
  `hf_repo_id` LONGTEXT NOT NULL DEFAULT 'Logics-MLLM/Logics-Parsing-v2',
  `ms_repo_id` LONGTEXT NOT NULL DEFAULT 'Alibaba-DT/Logics-Parsing-v2',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `email_mock` TINYINT(1) DEFAULT 1,
  `smtp_host` LONGTEXT,
  `smtp_port` INT DEFAULT 587,
  `smtp_user` LONGTEXT,
  `smtp_password` LONGTEXT,
  `smtp_from` LONGTEXT,
  `smtp_use_tls` TINYINT(1) DEFAULT 1,
  `register_email_enabled` TINYINT(1) DEFAULT 1,
  `register_phone_enabled` TINYINT(1) DEFAULT 1,
  `login_email_enabled` TINYINT(1) DEFAULT 1,
  `login_phone_enabled` TINYINT(1) DEFAULT 1,
  `forgot_email_enabled` TINYINT(1) DEFAULT 1,
  `forgot_phone_enabled` TINYINT(1) DEFAULT 1,
  `sms_mock` TINYINT(1) DEFAULT 1,
  `sms_http_url` LONGTEXT,
  `sms_http_secret` LONGTEXT,
  `sms_http_headers_json` LONGTEXT,
  `sms_http_body_template` LONGTEXT,
  `show_page_numbers` TINYINT(1) DEFAULT 1,
  `image_output_mode` LONGTEXT DEFAULT 'base64',
  `stale_job_timeout_minutes` INT NOT NULL DEFAULT 10,
  `login_timeout_minutes` INT DEFAULT 10,
  `password_min_length` INT DEFAULT 8,
  `password_require_uppercase` TINYINT(1) DEFAULT 1,
  `password_require_lowercase` TINYINT(1) DEFAULT 1,
  `password_require_digit` TINYINT(1) DEFAULT 1,
  `password_require_special` TINYINT(1) DEFAULT 0,
  `max_upload_size_mb` INT DEFAULT 50,
  `allow_multi_file_upload` TINYINT(1) DEFAULT 1,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 插入默认管理员账号（密码: admin123）
-- 注意：实际部署时应修改此密码
INSERT INTO `users` (`id`, `email`, `username`, `hashed_password`, `is_active`, `is_admin`, `created_at`) VALUES
  (1, 'admin@logics-parsing.local', 'admin', '$2b$12$I0VJKvfMeRGtLYWXr0pRZObYDNgovHCKbcQa3koDVSOpQazGF6J0u', 1, 1, NOW());

-- 插入默认系统配置
INSERT INTO `app_settings` (
  `id`,
  `registration_enabled`,
  `captcha_login_enabled`,
  `captcha_register_enabled`,
  `captcha_forgot_enabled`,
  `pdf_max_pages`,
  `hf_repo_id`,
  `ms_repo_id`,
  `updated_at`,
  `email_mock`,
  `smtp_port`,
  `smtp_use_tls`,
  `register_email_enabled`,
  `register_phone_enabled`,
  `login_email_enabled`,
  `login_phone_enabled`,
  `forgot_email_enabled`,
  `forgot_phone_enabled`,
  `sms_mock`,
  `show_page_numbers`,
  `image_output_mode`,
  `stale_job_timeout_minutes`,
  `login_timeout_minutes`,
  `password_min_length`,
  `password_require_uppercase`,
  `password_require_lowercase`,
  `password_require_digit`,
  `password_require_special`,
  `max_upload_size_mb`,
  `allow_multi_file_upload`
) VALUES (
  1,
  1,   -- registration_enabled
  0,   -- captcha_login_enabled
  0,   -- captcha_register_enabled
  0,   -- captcha_forgot_enabled
  80,  -- pdf_max_pages
  'Logics-MLLM/Logics-Parsing-v2',  -- hf_repo_id
  'Alibaba-DT/Logics-Parsing-v2',   -- ms_repo_id
  NOW(),  -- updated_at
  1,     -- email_mock
  587,   -- smtp_port
  1,     -- smtp_use_tls
  1,     -- register_email_enabled
  1,     -- register_phone_enabled
  1,     -- login_email_enabled
  1,     -- login_phone_enabled
  1,     -- forgot_email_enabled
  1,     -- forgot_phone_enabled
  1,     -- sms_mock
  1,     -- show_page_numbers
  'base64',  -- image_output_mode
  10,    -- stale_job_timeout_minutes
  10,    -- login_timeout_minutes
  8,     -- password_min_length
  1,     -- password_require_uppercase
  1,     -- password_require_lowercase
  1,     -- password_require_digit
  0,     -- password_require_special
  50,    -- max_upload_size_mb
  1      -- allow_multi_file_upload
);

-- 创建索引以提高查询性能
CREATE INDEX idx_users_email ON users(email(100));
CREATE INDEX idx_parse_jobs_user_id ON parse_jobs(user_id);
CREATE INDEX idx_parse_jobs_status ON parse_jobs(status(50));
CREATE INDEX idx_verification_codes_email ON verification_codes(email(100));
CREATE INDEX idx_verification_codes_expires_at ON verification_codes(expires_at);

SET FOREIGN_KEY_CHECKS = 1;
