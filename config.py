import os

class Config(object):
    # The value of the secret key is used as a cryptographic key for generating signatures/tokens
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    #------------------------------------------
    # Configure the database connection
    #------------------------------------------
    MYSQL_HOST = os.environ.get('MYSQL_HOST') or 'localhost'
    MYSQL_USER = os.environ.get('MYSQL_USER') or 'CapstoneMySQLUser'
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD') or 'CapstoneMySQLUserDbPw'
    MYSQL_DB = os.environ.get('MYSQL_DB') or 'CapstoneData'


