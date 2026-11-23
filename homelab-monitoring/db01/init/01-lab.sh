#!/bin/bash
# Runs once, on first start of an empty data volume (official mariadb image hook)
mariadb -uroot -p"${MARIADB_ROOT_PASSWORD}" <<SQL
CREATE DATABASE IF NOT EXISTS labdb;
USE labdb;
CREATE TABLE IF NOT EXISTS customers (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(80) NOT NULL,
  city VARCHAR(80) NOT NULL
);
INSERT INTO customers (name, city) VALUES
  ('Asha Rao','Pune'), ('Ravi Kumar','Chennai'), ('Meera Iyer','Bengaluru'),
  ('Karan Shah','Mumbai'), ('Neha Gupta','Delhi');
CREATE USER IF NOT EXISTS 'nagios'@'%' IDENTIFIED BY '${NAGIOS_DB_PASS}';
GRANT SELECT ON labdb.* TO 'nagios'@'%';
FLUSH PRIVILEGES;
SQL
