from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect
from sqlalchemy.orm import relationship, validates
import uuid
import datetime

from database import db
from utils import eprint, is_emoji

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    twitter_id = db.Column(db.Integer, index=True, unique=True)
    screen_name = db.Column(db.Text)
    name = db.Column(db.Text)
    profile_image_url = db.Column(db.Text)
    oauth_token = db.Column(db.Text)
    oauth_token_secret = db.Column(db.Text)

    definitions = relationship("Definition", back_populates="user")
    votes = relationship("Vote", back_populates="user")

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Word(db.Model):
    __tablename__ = 'words'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text, unique=True)

    definitions = relationship("Definition", back_populates="word")

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @validates('title')
    def validate_title(self, key, title):
        if not is_emoji(title):
            raise ValueError('Word should be a combination of up to 3 emoji')
        return title


class Definition(db.Model):
    __tablename__ = 'definitions'

    id = db.Column(db.Integer, primary_key=True)
    definition = db.Column(db.Text)

    word_id = db.Column(db.Integer, db.ForeignKey('words.id'))
    word = relationship("Word", back_populates="definitions")

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = relationship("User", back_populates="definitions")

    votes = relationship("Vote", back_populates="definition",  cascade="all, delete-orphan")

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class Vote(db.Model):
    __tablename__ = 'votes'

    id = db.Column(db.Integer, primary_key=True)
    vote = db.Column(db.Integer) # 1/-1

    definition_id = db.Column(db.Integer, db.ForeignKey('definitions.id'))
    definition = relationship("Definition", back_populates="votes")

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = relationship("User", back_populates="votes")

