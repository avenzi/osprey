from app import mysql

# Flask imports
from flask import render_template

class View:
    def __init__(self):
        self.database_cursor = mysql.connection.cursor()
    
    def render(self, name, **kwargs):
        return render_template(name, **kwargs)
