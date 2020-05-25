import os

# Flask configuration file
class Config(object):
    # The value of the secret key is used as a cryptographic key for generating signatures/tokens
    SECRET_KEY = os.environ.get("SECRET_KEY") or "you-will-never-guess"

    #------------------------------------------
    # Configure the database connection
    #------------------------------------------
    MYSQL_HOST = os.environ.get("MYSQL_HOST") or "localhost"
    MYSQL_USER = os.environ.get("MYSQL_USER") or "CapstoneMySQLUser"
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD") or "CapstoneMySQLUserDbPw"
    MYSQL_DB = os.environ.get("MYSQL_DB") or "CapstoneData"


    # Replace /root/capstone-site with the absolute path of where
    # the repository is installed on the system.
    UPLOADS_FOLDER = os.environ.get("UPLOADS_FOLDER") or "~/data-hub/app/static/uploads/"
    DOWNLOADS_FOLDER = os.environ.get("DOWNLOADS_FOLDER") or "~/data-hub/app/static/downloads/"
