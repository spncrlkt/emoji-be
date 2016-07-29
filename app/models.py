from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect
from sqlalchemy.orm import relationship
import uuid
import datetime

from database import db
from utils import eprint

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    twitter_id = db.Column(db.Integer, index=True, unique=True)
    screen_name = db.Column(db.Text)
    oauth_token = db.Column(db.Text)
    oauth_token_secret = db.Column(db.Text)

    definitions = relationship("Definition")


class Word(db.Model):
    __tablename__ = 'words'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text)

    definitions = relationship("Definition")


class Definition(db.Model):
    __tablename__ = 'definitions'

    id = db.Column(db.Integer, primary_key=True)
    definition = db.Column(db.Text)
    upvotes = db.Column(db.Integer, default=0)
    downvotes = db.Column(db.Integer, default=0)

    word_id = db.Column(db.Integer, db.ForeignKey('words.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
