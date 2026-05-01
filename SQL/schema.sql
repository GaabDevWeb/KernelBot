CREATE TABLE IF NOT EXISTS `knowledge` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `title` varchar(255) NOT NULL,
  `slug` varchar(255) NOT NULL,
  `description` varchar(2000) NOT NULL,
  `order` int(11) NOT NULL DEFAULT 0,
  `keywords` varchar(2000) DEFAULT NULL,
  `learning_objectives` varchar(2000) DEFAULT NULL,
  `content` text NOT NULL,
  `discipline` varchar(70) NOT NULL,
  `concepts` varchar(2000) DEFAULT NULL,
  `active` bigint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=54 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;