-- MySQL Workbench Forward Engineering

SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';

-- -----------------------------------------------------
-- Schema webcrawler
-- -----------------------------------------------------

-- -----------------------------------------------------
-- Schema webcrawler
-- -----------------------------------------------------
CREATE SCHEMA IF NOT EXISTS `webcrawler` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci ;
USE `webcrawler` ;

-- -----------------------------------------------------
-- Table `webcrawler`.`Scans`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `webcrawler`.`Scans` ;

CREATE TABLE IF NOT EXISTS `webcrawler`.`Scans` (
  `scan_id` INT(11) NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(45) NOT NULL,
  `description` TEXT NULL DEFAULT NULL,
  `start_timestamp` DATETIME NULL DEFAULT NULL,
  `end_timestamp` DATETIME NULL DEFAULT NULL,
  `seed_url` TEXT NULL DEFAULT NULL,
  `search_fqdn_re` TEXT NULL DEFAULT NULL,
  `sub_path_re` TEXT NULL DEFAULT NULL,
  PRIMARY KEY (`scan_id`),
  UNIQUE INDEX `name_UNIQUE` (`name` ASC),
  UNIQUE INDEX `scan_id_UNIQUE` (`scan_id` ASC))
ENGINE = InnoDB
AUTO_INCREMENT = 1
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;


-- -----------------------------------------------------
-- Table `webcrawler`.`FoundURLs`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `webcrawler`.`FoundURLs` ;

CREATE TABLE IF NOT EXISTS `webcrawler`.`FoundURLs` (
  `url_id` INT(11) NOT NULL AUTO_INCREMENT,
  `scan_id` INT(11) NOT NULL,
  `url_hash` VARCHAR(64) NOT NULL,
  `url_text` TEXT NULL DEFAULT NULL,
  `root_stem` VARCHAR(512) NULL DEFAULT NULL,
  `fqdn` TEXT NULL DEFAULT NULL,
  `is_crawled` TINYINT(4) NULL DEFAULT NULL,
  `is_blacklisted` TINYINT(4) NULL DEFAULT NULL,
  `next_url_id` INT(11) NULL DEFAULT NULL,
  `status_code` VARCHAR(3) NULL DEFAULT NULL,
  `content_type` VARCHAR(128) NULL DEFAULT NULL,
  `page_title` TEXT NULL DEFAULT NULL,
  `created_timestamp` DATETIME NULL DEFAULT NULL,
  `crawled_timestamp` DATETIME NULL DEFAULT NULL,
  PRIMARY KEY (`url_id`),
  UNIQUE INDEX `UNIQUE-scan_id-url_hash` (`scan_id` ASC, `url_hash` ASC),
  INDEX `INDEX-scan_id-url_hash` (`scan_id` ASC, `url_hash` ASC),
  INDEX `idx_scan_id_root_stem` (`scan_id` ASC, `root_stem`(64) ASC),
  INDEX `idx_is_crawled` (`is_crawled` ASC),
  INDEX `idx_FoundURLs_root_stem` (`root_stem` ASC),
  INDEX `idx_FoundURLs_status_code` (`status_code` ASC),
  INDEX `fk_FoundURLs-next_url_id_idx` (`next_url_id` ASC),
  CONSTRAINT `fk_FoundURLs_PK`
    FOREIGN KEY (`scan_id`)
    REFERENCES `webcrawler`.`Scans` (`scan_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_FoundURLs-next_url_id`
    FOREIGN KEY (`next_url_id`)
    REFERENCES `webcrawler`.`FoundURLs` (`url_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB
AUTO_INCREMENT = 1
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;


-- -----------------------------------------------------
-- Table `webcrawler`.`Backlinks`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `webcrawler`.`Backlinks` ;

CREATE TABLE IF NOT EXISTS `webcrawler`.`Backlinks` (
  `url_id` INT(11) NOT NULL,
  `backlink_url_id` INT(11) NOT NULL,
  `backlink_timestamp` DATETIME NULL DEFAULT NULL,
  INDEX `fk-Backlinks-backlink_url_id_idx` (`backlink_url_id` ASC),
  INDEX `fk-Backlinks-url_id` (`url_id` ASC),
  CONSTRAINT `fk-Backlinks-backlink_url_id`
    FOREIGN KEY (`backlink_url_id`)
    REFERENCES `webcrawler`.`FoundURLs` (`url_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk-Backlinks-url_id`
    FOREIGN KEY (`url_id`)
    REFERENCES `webcrawler`.`FoundURLs` (`url_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;


-- -----------------------------------------------------
-- Table `webcrawler`.`PageLinks`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `webcrawler`.`PageLinks` ;

CREATE TABLE IF NOT EXISTS `webcrawler`.`PageLinks` (
  `url_id` INT(11) NOT NULL,
  `link` TEXT NOT NULL,
  `linktext` TEXT NULL DEFAULT NULL,
  INDEX `fk-PageLinks-url_id_idx` (`url_id` ASC),
  CONSTRAINT `fk-PageLinks-url_id`
    FOREIGN KEY (`url_id`)
    REFERENCES `webcrawler`.`FoundURLs` (`url_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;


-- -----------------------------------------------------
-- Table `webcrawler`.`ScanBlackLists`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `webcrawler`.`ScanBlackLists` ;

CREATE TABLE IF NOT EXISTS `webcrawler`.`ScanBlackLists` (
  `scan_id` INT(11) NOT NULL,
  `fqdn` VARCHAR(512) NOT NULL,
  `path` VARCHAR(2048) NULL DEFAULT NULL,
  `scheme` VARCHAR(2048) NULL DEFAULT NULL,
  `netloc` VARCHAR(2048) NULL DEFAULT NULL,
  INDEX `fk_ScanBlackLists-scan_id` (`scan_id` ASC),
  CONSTRAINT `fk_ScanBlackLists-scan_id`
    FOREIGN KEY (`scan_id`)
    REFERENCES `webcrawler`.`Scans` (`scan_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;


-- -----------------------------------------------------
-- Table `webcrawler`.`ScanErrors`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `webcrawler`.`ScanErrors` ;

CREATE TABLE IF NOT EXISTS `webcrawler`.`ScanErrors` (
  `url_id` INT(11) NOT NULL,
  `error_text` TEXT NULL DEFAULT NULL,
  `error_timestamp` DATETIME NULL DEFAULT NULL,
  INDEX `fk_ScanErrors-url_id` (`url_id` ASC),
  CONSTRAINT `fk_ScanErrors-url_id`
    FOREIGN KEY (`url_id`)
    REFERENCES `webcrawler`.`FoundURLs` (`url_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;


-- -----------------------------------------------------
-- Table `webcrawler`.`ScanRoots`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `webcrawler`.`ScanRoots` ;

CREATE TABLE IF NOT EXISTS `webcrawler`.`ScanRoots` (
  `scan_id` INT(11) NOT NULL,
  `fqdn` VARCHAR(512) NOT NULL,
  `port` VARCHAR(5) NULL DEFAULT NULL,
  UNIQUE INDEX `idx_ScanRoots_UNIQUE` (`scan_id` ASC, `fqdn` ASC, `port` ASC),
  CONSTRAINT `fk_ScanRoots-scan_id`
    FOREIGN KEY (`scan_id`)
    REFERENCES `webcrawler`.`Scans` (`scan_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;


SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;
