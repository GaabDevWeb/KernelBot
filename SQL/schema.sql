CREATE TABLE IF NOT EXISTS knowledge (
    id               INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    slug             VARCHAR(255)   NOT NULL,
    discipline       VARCHAR(70)    NOT NULL,
    title            VARCHAR(255)   NOT NULL,
    `order`          INT            NOT NULL DEFAULT 0,
    content          MEDIUMTEXT     NOT NULL,
    payload          JSON           NOT NULL,
    payload_version  SMALLINT       NOT NULL DEFAULT 1,
    source_checksum  CHAR(64)       NOT NULL,
    active           TINYINT(1)     NOT NULL DEFAULT 1,
    created_at       TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_slug (slug),
    KEY idx_active_discipline (active, discipline),
    KEY idx_discipline_order (discipline, `order`),
    CONSTRAINT chk_payload_json CHECK (JSON_VALID(payload))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
