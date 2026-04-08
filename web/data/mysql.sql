-- ============================================
-- SQLite to MySQL Migration Script
-- Generated at: 2026-04-08 10:51:21
-- ============================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- 表: users
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `id` INT NOT NULL,
  `email` LONGTEXT NOT NULL,
  `username` LONGTEXT NOT NULL,
  `hashed_password` LONGTEXT NOT NULL,
  `is_active` TINYINT(1) NOT NULL,
  `failed_login_attempts` INT NOT NULL,
  `locked_until` DATETIME,
  `created_at` DATETIME NOT NULL,
  `is_admin` TINYINT(1) DEFAULT '0',
  `phone` LONGTEXT,
  `pdf_max_pages` INT,
  `can_download_images` TINYINT(1) DEFAULT '1',
  `image_output_mode` LONGTEXT DEFAULT 'NULL',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 数据: users (2 行)
INSERT INTO `users` (`id`, `email`, `username`, `hashed_password`, `is_active`, `failed_login_attempts`, `locked_until`, `created_at`, `is_admin`, `phone`, `pdf_max_pages`, `can_download_images`, `image_output_mode`) VALUES
  (2, 'admin@logics-parsing.local', 'admin', '$2b$12$I0VJKvfMeRGtLYWXr0pRZObYDNgovHCKbcQa3koDVSOpQazGF6J0u', 1, 0, NULL, '2026-04-06 10:45:06.759530', 1, NULL, NULL, 1, NULL),
  (3, 'sunyd168@126.com', 'sunyd168', '$2b$12$0JOsIx3sgyYPoR5v.fxni.Z64Jx4HOl2pLmqmufQlRpRVh8S9Ozwe', 1, 0, NULL, '2026-04-06 13:40:01.351105', 0, NULL, NULL, 1, NULL);


-- 表: verification_codes
DROP TABLE IF EXISTS `verification_codes`;
CREATE TABLE `verification_codes` (
  `id` INT NOT NULL,
  `email` LONGTEXT NOT NULL,
  `code_hash` LONGTEXT NOT NULL,
  `expires_at` DATETIME NOT NULL,
  `created_at` DATETIME NOT NULL,
  `purpose` LONGTEXT DEFAULT ''register'',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- 表: parse_jobs
DROP TABLE IF EXISTS `parse_jobs`;
CREATE TABLE `parse_jobs` (
  `job_id` LONGTEXT NOT NULL,
  `user_id` INT NOT NULL,
  `created_at` DATETIME NOT NULL,
  `status` LONGTEXT DEFAULT ''processing'',
  `original_filename` LONGTEXT,
  `completed_at` DATETIME,
  `cache_cleared_at` DATETIME,
  `pages_parsed` INT,
  PRIMARY KEY (`job_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 数据: parse_jobs (7 行)
INSERT INTO `parse_jobs` (`job_id`, `user_id`, `created_at`, `status`, `original_filename`, `completed_at`, `cache_cleared_at`, `pages_parsed`) VALUES
  ('cfab9b27-612a-47b3-ac48-d9ac3b7fe016', 2, '2026-04-06 14:33:31.497325', 'stopped', 'Git教程-廖雪峰-2025-06-16.pdf', '2026-04-06 14:33:51.462894', NULL, 1),
  ('110ba84c-f4a4-4574-b466-eedf969d1513', 2, '2026-04-06 16:13:25.388609', 'completed', 'Git教程-廖雪峰-2025-06-16.pdf', '2026-04-06 16:14:03.442961', NULL, 5),
  ('937dd0fc-c12a-428b-85f8-3b8c7d6769cf', 2, '2026-04-06 16:17:17.722698', 'completed', 'Git教程-廖雪峰-2025-06-16.pdf', '2026-04-06 16:17:55.171656', NULL, 5),
  ('45438b9c-31ac-4e78-b7a8-e0709b7cc674', 2, '2026-04-06 16:19:05.098872', 'completed', 'Git教程-廖雪峰-2025-06-16.pdf', '2026-04-06 16:19:43.016508', NULL, 5),
  ('32768b78-7578-452f-9346-92b2f9f172fd', 2, '2026-04-06 16:23:54.385151', 'completed', 'Git教程-廖雪峰-2025-06-16.pdf', '2026-04-06 16:24:32.475867', NULL, 5),
  ('154297b0-7d14-4f4c-8591-6c5a0f39779f', 3, '2026-04-06 23:10:15.260357', 'completed', 'Git教程-廖雪峰-2025-06-16.pdf', '2026-04-06 23:10:20.063115', NULL, 1),
  ('d150db7f-a661-44b6-909d-8a324116c877', 2, '2026-04-07 00:56:09.685400', 'completed', 'Git教程-廖雪峰-2025-06-16.pdf', '2026-04-07 00:56:14.828055', NULL, 1);


-- 表: app_settings
DROP TABLE IF EXISTS `app_settings`;
CREATE TABLE `app_settings` (
  `id` INT NOT NULL,
  `registration_enabled` TINYINT(1) NOT NULL,
  `captcha_login_enabled` TINYINT(1) NOT NULL,
  `captcha_register_enabled` TINYINT(1) NOT NULL,
  `captcha_forgot_enabled` TINYINT(1) NOT NULL,
  `pdf_max_pages` INT NOT NULL,
  `output_dir` LONGTEXT,
  `model_local_path` LONGTEXT,
  `hf_repo_id` LONGTEXT NOT NULL,
  `ms_repo_id` LONGTEXT NOT NULL,
  `updated_at` DATETIME,
  `email_mock` TINYINT(1) DEFAULT '1',
  `smtp_host` LONGTEXT,
  `smtp_port` INT DEFAULT '587',
  `smtp_user` LONGTEXT,
  `smtp_password` LONGTEXT,
  `smtp_from` LONGTEXT,
  `smtp_use_tls` TINYINT(1) DEFAULT '1',
  `register_email_enabled` TINYINT(1) DEFAULT '1',
  `register_phone_enabled` TINYINT(1) DEFAULT '1',
  `login_email_enabled` TINYINT(1) DEFAULT '1',
  `login_phone_enabled` TINYINT(1) DEFAULT '1',
  `forgot_email_enabled` TINYINT(1) DEFAULT '1',
  `forgot_phone_enabled` TINYINT(1) DEFAULT '1',
  `sms_mock` TINYINT(1) DEFAULT '1',
  `sms_http_url` LONGTEXT,
  `sms_http_secret` LONGTEXT,
  `sms_http_headers_json` LONGTEXT,
  `sms_http_body_template` LONGTEXT,
  `show_page_numbers` TINYINT(1) DEFAULT '1',
  `image_output_mode` LONGTEXT DEFAULT ''base64'',
  `stale_job_timeout_minutes` INT NOT NULL DEFAULT '10',
  `login_timeout_minutes` INT DEFAULT '10',
  `password_min_length` INT DEFAULT '8',
  `password_require_uppercase` TINYINT(1) DEFAULT '1',
  `password_require_lowercase` TINYINT(1) DEFAULT '1',
  `password_require_digit` TINYINT(1) DEFAULT '1',
  `password_require_special` TINYINT(1) DEFAULT '0',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 数据: app_settings (1 行)
INSERT INTO `app_settings` (`id`, `registration_enabled`, `captcha_login_enabled`, `captcha_register_enabled`, `captcha_forgot_enabled`, `pdf_max_pages`, `output_dir`, `model_local_path`, `hf_repo_id`, `ms_repo_id`, `updated_at`, `email_mock`, `smtp_host`, `smtp_port`, `smtp_user`, `smtp_password`, `smtp_from`, `smtp_use_tls`, `register_email_enabled`, `register_phone_enabled`, `login_email_enabled`, `login_phone_enabled`, `forgot_email_enabled`, `forgot_phone_enabled`, `sms_mock`, `sms_http_url`, `sms_http_secret`, `sms_http_headers_json`, `sms_http_body_template`, `show_page_numbers`, `image_output_mode`, `stale_job_timeout_minutes`, `login_timeout_minutes`, `password_min_length`, `password_require_uppercase`, `password_require_lowercase`, `password_require_digit`, `password_require_special`) VALUES
  (1, 1, 0, 0, 0, 80, NULL, 'weights', 'Logics-MLLM/Logics-Parsing-v2', 'Alibaba-DT/Logics-Parsing-v2', '2026-04-06 23:23:54.430954', 1, NULL, 587, NULL, NULL, NULL, 1, 1, 1, 1, 1, 1, 1, 1, NULL, NULL, NULL, NULL, 0, 'separate', 10, 10, 8, 0, 1, 1, 0);


SET FOREIGN_KEY_CHECKS = 1;
