import sys
import traceback
import inspect
import os
import json
import requests
from flask import Flask, jsonify, request, session
from flask import g, url_for,  redirect, render_template
from flask_oauthlib.client import OAuth
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS, cross_origin
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import NoResultFound

import tweepy

from werkzeug.utils import secure_filename

from random import random
import math

from utils import eprint, epprint
from database import db
from models import User, Word, Definition

from invalid_usage import InvalidUsage

app = Flask(__name__)
cors = CORS(app, origins=[
    "http://0.0.0.0",
    "http://localhost",
    "http://staging.emojeni.us"
    "http://emojeni.us"
])

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

@app.route('/')
def index():
    if g.user:
        return 'logged in'
    return 'not logged in'


@app.route('/health')
def health():
    return 'OK'

# twitter oauth

oauth = OAuth(app)

twitter = oauth.remote_app(
    'twitter',
    consumer_key=app.config.get('TW_KEY'),
    consumer_secret=app.config.get('TW_SECRET'),
    base_url='https://api.twitter.com/1.1/',
    request_token_url='https://api.twitter.com/oauth/request_token',
    access_token_url='https://api.twitter.com/oauth/access_token',
    authorize_url='https://api.twitter.com/oauth/authorize',
)


@twitter.tokengetter
def get_twitter_token():
    if 'twitter_oauth' in session:
        resp = session['twitter_oauth']
        return resp['oauth_token'], resp['oauth_token_secret']

@app.before_request
def before_request():
    g.user = None
    if 'twitter_oauth' in session:
        g.user = session['twitter_oauth']

@app.route('/login')
def login():
    callback_url = url_for('oauthorized', next=request.args.get('next'))
    return twitter.authorize(callback=callback_url or request.referrer or None)


@app.route('/logout')
def logout():
    session.pop('twitter_oauth', None)
    return redirect(url_for('index'))


@app.route('/oauthorized')
def oauthorized():
    resp = twitter.authorized_response()
    if resp is None:
        return 'You denied the request to sign in.'
    else:
        try:
            user = db.session.query(User).filter_by(twitter_id=resp['user_id']).one()
        except NoResultFound as ex:
            user = User()
        # Set OAuth info
        user.twitter_id = resp['user_id']
        user.screen_name = resp['screen_name']
        user.oauth_token = resp['oauth_token']
        user.oauth_token_secret = resp['oauth_token_secret']

        # get addl user info
        consumer_key=app.config.get('TW_KEY'),
        consumer_secret=app.config.get('TW_SECRET'),

        auth = tweepy.OAuthHandler(consumer_key[0], consumer_secret[0])
        auth.set_access_token(
            resp['oauth_token'],
            resp['oauth_token_secret']
        )

        api = tweepy.API(auth)
        twitter_user = api.get_user(resp['user_id'])
        eprint('\n\n**********')
        epprint(twitter_user)
        eprint('\n\n**********')

        user.profile_image_url = twitter_user.profile_image_url
        user.name = twitter_user.name

        db.session.add(user)
        db.session.commit()
    next_url = request.args.get('next') + '/#/login/' + resp.get('user_id')
    return redirect(next_url)

@app.route('/user/<id>')
def user(id):
    try:
        user = db.session.query(User).filter_by(twitter_id=id).one()
    except NoResultFound as ex:
        return jsonify({'error': 'No User Found'})

    return jsonify({
        'user_id': user.twitter_id,
        'screen_name': user.screen_name
    })

@app.route('/word/add/<word>')
def add_word(word):
    try:
        existing_word = db.session.query(Word).filter_by(title=word).one()
        return jsonify({'error': 'Word already exists'})
    except NoResultFound as ex:
        new_word = Word()
        new_word.title = word
        db.session.add(new_word)
        db.session.commit()
        return jsonify({'id': new_word.id})

@app.route('/words')
def get_words():
    words = Word.query.all()
    res = []
    for word in words:
        word_res = {}
        word_res['id'] = word.id
        word_res['title'] = word.title
        word_res['definitions'] = list(map(lambda x : x.as_dict(), word.definitions))
        res.append(word_res)

    return jsonify({'words': res})

@app.route('/word/<title>')
def get_word(title):
    try:
        word = db.session.query(Word).\
            options(joinedload('definitions')).\
            filter_by(title=title).one()
    except NoResultFound as ex:
        return jsonify({'error': 'Word does not exist'})

    res_word = word.as_dict()

    def format_definition(definition):
        formatted = definition.as_dict()
        user = definition.user.as_dict()
        del user['oauth_token']
        del user['oauth_token_secret']
        formatted['user'] = user
        return formatted


    res_word['definitions'] = list(map(format_definition, word.definitions))
    return jsonify({ 'word': res_word })

@app.route('/word/<title>/definition', methods=['POST'])
def add_definition(title):
    body = request.get_json()
    try:
        word = db.session.query(Word).filter_by(title=title).one()
    except NoResultFound as ex:
        return jsonify({'error': 'Word does not exist'})

    posted_definition = body.get('definition')
    if not posted_definition:
        return jsonify({'error': 'Definition not supplied'})


    definition = Definition()
    definition.word_id = word.id
    definition.definition = posted_definition
    db.session.add(definition)
    db.session.commit()
    return jsonify({'definition': { 'id': definition.id}})


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
