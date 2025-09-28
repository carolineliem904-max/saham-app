CREATE DATABASE IF NOT EXISTS data_saham;
USE data_saham;

-- Master table
DROP TABLE IF EXISTS kumpulan_saham;
CREATE TABLE kumpulan_saham (
    id INT AUTO_INCREMENT PRIMARY KEY,
    Tanggal DATE,
    Nama_Saham VARCHAR(10),
    Sektor VARCHAR(100),
    Kepemilikan VARCHAR(100),
    Harga INT,
    Volume BIGINT,
    Market_Cap BIGINT
);

-- Historical table
DROP TABLE IF EXISTS histori_saham;
CREATE TABLE histori_saham (
    Nama_Saham VARCHAR(20) NOT NULL,
    Tanggal DATE NOT NULL,
    Terakhir DECIMAL(15,2),
    Pembukaan DECIMAL(15,2),
    Tertinggi DECIMAL(15,2),
    Terendah DECIMAL(15,2),
    Vol BIGINT,
    PerubahanPercent DECIMAL(8,2),
    PRIMARY KEY (Nama_Saham, Tanggal)
);
