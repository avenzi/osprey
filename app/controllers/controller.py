from app import mysql

# Flask imports
from flask import redirect, url_for

class Controller:
    def __init__(self):
        self.database_connection = mysql.connection
        self.database_cursor = mysql.connection.cursor()
    
    def redirect(self, route):
        return redirect(url_for(route))
    