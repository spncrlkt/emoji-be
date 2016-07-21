import sys
import traceback
import inspect
import os
import json
import requests
from flask import Flask, jsonify, request, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.utils import secure_filename

from random import random
import math

from utils import eprint
from database import db

from invalid_usage import InvalidUsage

app = Flask(__name__)

db_uri = 'postgresql+psycopg2://postgres:postgres@postgres:5432'

UPLOAD_FOLDER = os.path.dirname(
    os.path.abspath(
        inspect.getfile(
            inspect.currentframe()
        )
    )
) + '/uploads'

ALLOWED_EXTENSIONS = set(['json'])


app.config.update(dict(
    SQLALCHEMY_DATABASE_URI='{}/dev'.format(db_uri),
    DEBUG=True,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    UPLOAD_FOLDER=UPLOAD_FOLDER,
))
app.config.from_envvar('APP_SETTINGS', silent=True)

db.init_app(app)

# comments

@app.route('/')
def hello_world():
    return 'index'

@app.route('/health')
def health():
    return 'OK'

def create_tables():
    db.create_all()
    return 'created db tables'

def drop_tables():
    db.drop_all()
    return 'dropped db tables'

@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

@app.errorhandler(Exception)
def all_error_handler(error):
    eprint('\n**********')
    eprint('\nUnhandled Exception')
    traceback.print_exc(file=sys.stderr)
    eprint('\n**********')
    return 'Error', 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
