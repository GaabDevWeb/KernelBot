-- Schema `knowledge` — compatível com ISS ingest-knowledge.py e KernelBot engine/database.py
-- Executado automaticamente no primeiro boot do container (docker-entrypoint-initdb.d).

CREATE DATABASE IF NOT EXISTS kernelbot_staging
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE kernelbot_staging;

CREATE TABLE IF NOT EXISTS knowledge (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  discipline VARCHAR(128) NOT NULL,
  slug VARCHAR(255) NOT NULL,
  title VARCHAR(512) NOT NULL,
  `order` INT NOT NULL DEFAULT 0,
  content LONGTEXT,
  active TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_discipline_slug (discipline, slug),
  KEY idx_active (active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
