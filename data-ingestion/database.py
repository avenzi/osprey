import pymysql.cursors
import json

# Utility imports
from utils import Utils

class Database():
    tables = [
        "Sense",
        "VideoFrames",
        "AudioSegments",
        "Session",
        "SessionSensor"
    ]
    
    def get_connection(self):
        config = Utils().get_config()

        # Set up Database Connection using configured connection parameters
        db_connection = pymysql.connect(
            host=config["DATA_INGESTION_MYSQL_HOST"],
            user=config["DATA_INGESTION_MYSQL_USER"],
            password=config["DATA_INGESTION_MYSQL_PASSWORD"],
            db=config["DATA_INGESTION_MYSQL_DATABASE"],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True
        )

        return db_connection, db_connection.cursor()
    
    def ensure_schema(self):
        db_connection, cursor = self.get_connection()

        sql = """CREATE TABLE IF NOT EXISTS `Session`(
            id INT(11) NOT NULL AUTO_INCREMENT,
            StartDate DATETIME(3) NOT NULL,
            EndDate DATETIME(3) NULL,
            SensorConfig JSON NOT NULL,
            PRIMARY KEY (id)
        );"""
        cursor.execute(sql)

        sql = """CREATE TABLE IF NOT EXISTS `SessionSensor`(
            id INT(11) NOT NULL AUTO_INCREMENT,
            IP INT UNSIGNED NOT NULL,
            Name TINYTEXT NOT NULL,
            SessionId INT(11) NOT NULL,
            SensorType TINYTEXT,
            PRIMARY KEY (id)
        );"""
        cursor.execute(sql)

        sql = """
        CREATE TABLE IF NOT EXISTS `Sense`(
            id INT(11) NOT NULL AUTO_INCREMENT,
            IP INT UNSIGNED NOT NULL, 
            Time DATETIME(3) NOT NULL,
            Temp FLOAT(6, 2),
            Press FLOAT(6, 2),
            Humid FLOAT(6, 2),
            SessionId INT(11) NOT NULL,
            SensorId INT(11) NOT NULL,
            PRIMARY KEY (id)
        );"""
        cursor.execute(sql)

        sql = """
        CREATE TABLE IF NOT EXISTS `VideoFrames`(
            id int(11) NOT NULL AUTO_INCREMENT,
            FirstFrameTimestamp DATETIME(3) NOT NULL,
            LastFrameTimestamp  DATETIME(3) NOT NULL,
            FirstFrameNumber INT(11) NOT NULL,
            LastFrameNumber INT(11) NOT NULL,
            SessionId INT(11) NOT NULL,
            SensorId INT(11) NOT NULL,
            FramesMetadata JSON NOT NULL,
            PRIMARY KEY (id)
        );"""
        cursor.execute(sql)

        sql = """
        CREATE TABLE IF NOT EXISTS `AudioSegments`(
            id int(11) NOT NULL AUTO_INCREMENT,
            FirstSegmentTimestamp DATETIME(3) NOT NULL,
            LastSegmentTimestamp  DATETIME(3) NOT NULL,
            FirstSegmentNumber INT(11) NOT NULL,
            LastSegmentNumber INT(11) NOT NULL,
            SessionId INT(11) NOT NULL,
            SensorId INT(11) NOT NULL,
            SegmentsMetadata JSON NOT NULL,
            PRIMARY KEY (id)
        );"""
        cursor.execute(sql)

        db_connection.commit()
        db_connection.close()
    
    def drop_all_tables(self):
        db_connection, cursor = self.get_connection()

        sql = "DROP TABLE IF EXISTS %s;"
        for table_name in self.tables:
            cursor.execute(sql % table_name)
        
        db_connection.commit()
        db_connection.close()
    
    def drop_table(self, table_name):
        db_connection, cursor = self.get_connection()

        sql = "DROP TABLE IF EXISTS %s;"
        cursor.execute(sql % table_name)
        
        db_connection.commit()
        db_connection.close()
