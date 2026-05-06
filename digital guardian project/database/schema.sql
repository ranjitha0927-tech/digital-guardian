CREATE DATABASE IF NOT EXISTS digital_guardian;
USE digital_guardian;

CREATE TABLE IF NOT EXISTS parent_users (
  id INT PRIMARY KEY AUTO_INCREMENT,
  parent_name VARCHAR(120) NOT NULL,
  email VARCHAR(160) NOT NULL UNIQUE,
  phone_number VARCHAR(40) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS admin_users (
  id INT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(80) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  last_login_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS child_profiles (
  id INT PRIMARY KEY AUTO_INCREMENT,
  parent_id INT NOT NULL,
  child_name VARCHAR(120) NOT NULL,
  child_username VARCHAR(80) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  age INT NOT NULL,
  gender VARCHAR(40) NOT NULL,
  grade VARCHAR(80) NOT NULL,
  school_name VARCHAR(180) NOT NULL,
  parent_contact VARCHAR(80) NOT NULL,
  device_name VARCHAR(120) NOT NULL,
  screen_time_limit_hours DECIMAL(5,2) NOT NULL DEFAULT 2.00,
  notes TEXT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_child_parent FOREIGN KEY (parent_id) REFERENCES parent_users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS restricted_keywords (
  id INT PRIMARY KEY AUTO_INCREMENT,
  keyword VARCHAR(120) NOT NULL UNIQUE,
  category VARCHAR(80) NOT NULL,
  severity VARCHAR(20) NOT NULL DEFAULT 'high',
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS browsing_history (
  id INT PRIMARY KEY AUTO_INCREMENT,
  parent_id INT NOT NULL,
  child_id INT NOT NULL,
  search_query VARCHAR(255) NOT NULL,
  site_url VARCHAR(255) NULL,
  device_name VARCHAR(120) NULL,
  activity_type VARCHAR(40) NOT NULL DEFAULT 'browser_search',
  matched_keyword VARCHAR(120) NULL,
  matched_category VARCHAR(80) NULL,
  is_restricted BOOLEAN NOT NULL DEFAULT FALSE,
  search_time DATETIME NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_history_parent FOREIGN KEY (parent_id) REFERENCES parent_users(id) ON DELETE CASCADE,
  CONSTRAINT fk_history_child FOREIGN KEY (child_id) REFERENCES child_profiles(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS safe_search_results (
  id INT PRIMARY KEY AUTO_INCREMENT,
  parent_id INT NOT NULL,
  child_id INT NOT NULL,
  history_id INT NULL,
  search_query VARCHAR(255) NOT NULL,
  matched_keyword VARCHAR(120) NULL,
  search_topic VARCHAR(120) NULL,
  is_restricted BOOLEAN NOT NULL DEFAULT FALSE,
  recommended_sites JSON NOT NULL,
  blocked_reason VARCHAR(255) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_safe_parent FOREIGN KEY (parent_id) REFERENCES parent_users(id) ON DELETE CASCADE,
  CONSTRAINT fk_safe_child FOREIGN KEY (child_id) REFERENCES child_profiles(id) ON DELETE CASCADE,
  CONSTRAINT fk_safe_history FOREIGN KEY (history_id) REFERENCES browsing_history(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS activity_logs (
  id INT PRIMARY KEY AUTO_INCREMENT,
  parent_id INT NOT NULL,
  child_id INT NOT NULL,
  event_type VARCHAR(40) NOT NULL,
  app_name VARCHAR(160) NULL,
  target_name VARCHAR(160) NULL,
  target_url VARCHAR(255) NULL,
  keyword VARCHAR(120) NULL,
  matched_category VARCHAR(80) NULL,
  details TEXT NULL,
  is_restricted BOOLEAN NOT NULL DEFAULT FALSE,
  occurred_at DATETIME NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_activity_parent FOREIGN KEY (parent_id) REFERENCES parent_users(id) ON DELETE CASCADE,
  CONSTRAINT fk_activity_child FOREIGN KEY (child_id) REFERENCES child_profiles(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS alerts (
  id INT PRIMARY KEY AUTO_INCREMENT,
  parent_id INT NOT NULL,
  child_id INT NOT NULL,
  history_id INT NULL,
  activity_id INT NULL,
  title VARCHAR(180) NOT NULL,
  description TEXT NOT NULL,
  severity VARCHAR(20) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'open',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_alert_parent FOREIGN KEY (parent_id) REFERENCES parent_users(id) ON DELETE CASCADE,
  CONSTRAINT fk_alert_child FOREIGN KEY (child_id) REFERENCES child_profiles(id) ON DELETE CASCADE,
  CONSTRAINT fk_alert_history FOREIGN KEY (history_id) REFERENCES browsing_history(id) ON DELETE SET NULL,
  CONSTRAINT fk_alert_activity FOREIGN KEY (activity_id) REFERENCES activity_logs(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS notifications (
  id INT PRIMARY KEY AUTO_INCREMENT,
  parent_id INT NOT NULL,
  child_id INT NULL,
  channel VARCHAR(40) NOT NULL DEFAULT 'sms',
  recipient VARCHAR(80) NOT NULL,
  provider VARCHAR(40) NOT NULL DEFAULT 'simulated_twilio',
  trigger_type VARCHAR(60) NOT NULL,
  title VARCHAR(180) NOT NULL,
  message TEXT NOT NULL,
  delivery_status VARCHAR(40) NOT NULL DEFAULT 'sent',
  meta_json JSON NULL,
  sent_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_notification_parent FOREIGN KEY (parent_id) REFERENCES parent_users(id) ON DELETE CASCADE,
  CONSTRAINT fk_notification_child FOREIGN KEY (child_id) REFERENCES child_profiles(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS ml_predictions (
  id INT PRIMARY KEY AUTO_INCREMENT,
  parent_id INT NOT NULL,
  child_id INT NOT NULL,
  history_id INT NULL,
  input_text VARCHAR(255) NOT NULL,
  rule_based_label VARCHAR(20) NOT NULL DEFAULT 'safe',
  ml_label VARCHAR(20) NOT NULL DEFAULT 'safe',
  final_label VARCHAR(20) NOT NULL DEFAULT 'safe',
  confidence_score DECIMAL(7,4) NOT NULL DEFAULT 0,
  anomaly_score DECIMAL(9,4) NULL,
  anomaly_detected BOOLEAN NOT NULL DEFAULT FALSE,
  model_name VARCHAR(80) NOT NULL DEFAULT 'tfidf-logistic-regression-v1',
  feature_json JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_ml_parent FOREIGN KEY (parent_id) REFERENCES parent_users(id) ON DELETE CASCADE,
  CONSTRAINT fk_ml_child FOREIGN KEY (child_id) REFERENCES child_profiles(id) ON DELETE CASCADE,
  CONSTRAINT fk_ml_history FOREIGN KEY (history_id) REFERENCES browsing_history(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS reports (
  id INT PRIMARY KEY AUTO_INCREMENT,
  parent_id INT NOT NULL,
  report_type VARCHAR(30) NOT NULL,
  week_label VARCHAR(50) NULL,
  month_label VARCHAR(50) NULL,
  screen_time_hours DECIMAL(10,2) NOT NULL DEFAULT 0,
  restricted_attempts_count INT NOT NULL DEFAULT 0,
  safe_browsing_score DECIMAL(5,2) NOT NULL DEFAULT 100,
  summary_json JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_report_parent FOREIGN KEY (parent_id) REFERENCES parent_users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS settings (
  id INT PRIMARY KEY AUTO_INCREMENT,
  parent_id INT NOT NULL UNIQUE,
  dark_mode BOOLEAN NOT NULL DEFAULT FALSE,
  help_email VARCHAR(160) NOT NULL DEFAULT 'support@digitalguardian.local',
  security_mode VARCHAR(40) NOT NULL DEFAULT 'enhanced',
  notification_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  email_notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  emergency_alerts_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  weekly_report_day VARCHAR(20) NOT NULL DEFAULT 'Sunday',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_settings_parent FOREIGN KEY (parent_id) REFERENCES parent_users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS admin_panel_settings (
  id INT PRIMARY KEY AUTO_INCREMENT,
  theme VARCHAR(30) NOT NULL DEFAULT 'pastel-blue',
  security_mode VARCHAR(40) NOT NULL DEFAULT 'strict',
  support_email VARCHAR(160) NOT NULL DEFAULT 'support@digitalguardian.local',
  app_info VARCHAR(255) NOT NULL DEFAULT 'Digital Guardian Admin Panel | Viva Demo Build',
  monitoring_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

INSERT IGNORE INTO restricted_keywords (keyword, category, severity) VALUES
('adult', 'adult content', 'critical'),
('adult website', 'adult content', 'critical'),
('adult websites', 'adult content', 'critical'),
('18+', 'adult content', 'critical'),
('porn', 'adult content', 'critical'),
('sex video', 'adult content', 'critical'),
('gambling', 'gambling', 'high'),
('betting', 'betting', 'high'),
('casino', 'gambling', 'high'),
('lottery', 'gambling', 'high'),
('odds', 'betting', 'medium'),
('harmful challenge', 'harmful websites', 'high'),
('self harm', 'harmful websites', 'critical'),
('dark web', 'unsafe website', 'high'),
('unsafe website', 'unsafe website', 'high'),
('unsafe websites', 'unsafe website', 'high'),
('harmful content', 'harmful websites', 'high');

INSERT IGNORE INTO admin_panel_settings (id, theme, security_mode, support_email, app_info, monitoring_enabled) VALUES
(1, 'pastel-blue', 'strict', 'support@digitalguardian.local', 'Digital Guardian Admin Panel | Viva Demo Build', TRUE);
