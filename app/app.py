import sys
import traceback
import inspect
import os
import json
import requests
import re
from flask import Flask, jsonify, request, session
from flask import g, url_for,  redirect, render_template
from flask_oauthlib.client import OAuth
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS, cross_origin
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import NoResultFound

from urllib.parse import urlparse, quote_plus
import traceback

import tweepy

from werkzeug.utils import secure_filename

from random import random
import math

from utils import encode_value, eprint, epprint, is_emoji
from database import db
from models import User, Word, Definition, Vote

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

        user.profile_image_url = twitter_user.profile_image_url
        user.name = twitter_user.name

        db.session.add(user)
        db.session.commit()

    url = urlparse(request.args.get('next'))
    m = re.search('#(.+)\?', request.args.get('next'))
    client_next_route = m.group(1)
    host = '{}://{}'.format(url.scheme, url.netloc)
    token = encode_value(
        resp['oauth_token'],
        app.config.get('AUTH_SALT')
    )
    next_url = host + '/#/login/' + resp.get('user_id') + '/' +\
            token + '/' + quote_plus(client_next_route)
    return redirect(next_url)

@app.route('/user/<id>/<auth_token>')
def user(id, auth_token):
    error = None
    try:
        user = db.session.query(User).filter_by(twitter_id=id).one()
    except NoResultFound as ex:
        error = 'Auth Error 1'
    encoded_token = encode_value(
        user.oauth_token,
        app.config.get('AUTH_SALT')
    )
    if auth_token != encoded_token:
        error = 'Auth Error 2'

    if error:
        return jsonify({'error': error})


    votes = {}
    for vote in user.votes:
        votes[vote.definition_id] = vote.vote

    definitions = {}
    for definition in user.definitions:
        definitions[definition.id] = definition.definition

    return jsonify({
        'twitter': {
            'userId': user.twitter_id,
            'screenName': user.screen_name
        },
        'votes': votes,
        'definitions': definitions
    })

@app.route('/word/add/<word>')
def add_word(word):
    try:
        existing_word = db.session.query(Word).filter_by(title=word).one()
        return jsonify({'error': 'Word already exists'})
    except NoResultFound as ex:
        try:
            new_word = Word()
            new_word.title = word
            db.session.add(new_word)
            db.session.commit()
            return jsonify({'id': new_word.id})
        except ValueError as ex:
            return jsonify({'error': str(ex)})

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

@app.route('/users')
def get_users():
    users = User.query.all()
    res = []
    for user in users:
        user_res = {}
        user_res['id'] = user.twitter_id
        user_res['name'] = user.name
        res.append(user_res)

    return jsonify({'users': res})

@app.route('/word/<title>')
def get_word(title):
    if not is_emoji(title):
        return jsonify({'error': 'Title must be a combination of up to 3 emoji'})

    try:
        word = db.session.query(Word).\
            options(joinedload('definitions')).\
            filter_by(title=title).one()
    except NoResultFound as ex:
        word = Word()
        word.title = title
        db.session.add(word)
        db.session.commit()

    res_word = word.as_dict()

    def format_definition(definition):
        formatted = definition.as_dict()

        user = definition.user.as_dict()
        del user['oauth_token']
        del user['oauth_token_secret']
        formatted['user'] = user

        votes = definition.votes
        upvotes = 0
        downvotes = 0
        for vote in votes:
            if vote.vote is 1:
                upvotes += 1
            else:
                downvotes += 1
        formatted['upvotes'] = upvotes
        formatted['downvotes'] = downvotes

        return formatted

    definitions = []
    for definition in word.definitions:
        formatted = format_definition(definition)
        definitions.append(formatted)

    def def_comp(definition):
        return definition['upvotes'] - definition['downvotes']

    sorted_definitions = sorted(definitions, key=def_comp, reverse=True)

    res_word['definitions'] = sorted_definitions
    return jsonify({ 'word': res_word })

@app.route('/word/<title>/definition', methods=['POST'])
def add_definition(title):
    body = request.get_json()
    try:
        word = db.session.query(Word).filter_by(title=title).one()
    except NoResultFound as ex:
        return jsonify({'error': 'Word does not exist'})

    posted_user_id = body.get('userId')
    if not posted_user_id:
        return jsonify({'error': 'User ID not supplied'})

    try:
        user = db.session.query(User).filter_by(twitter_id=posted_user_id).one()
    except NoResultFound as ex:
        return jsonify({'error': 'Auth Error'})

    posted_auth_token = body.get('authToken')
    token = encode_value(
        user.oauth_token,
        app.config.get('AUTH_SALT')
    )
    if token != posted_auth_token:
        return jsonify({'error': 'Auth Error'})

    try:
        definition = db.session.query(Definition)\
            .filter_by(user_id=user.id).filter_by(word_id=word.id).one()
        return jsonify({'error': 'Definition already exists'})
    except NoResultFound as ex:
        pass

    posted_definition = body.get('definition')
    if not posted_definition:
        return jsonify({'error': 'Definition not supplied'})


    definition = Definition()
    definition.word_id = word.id
    definition.user_id = user.id
    definition.definition = posted_definition
    db.session.add(definition)
    db.session.commit()
    return jsonify({'definition': { 'id': definition.id}})

@app.route('/word/<title>/definition/<definition_id>/delete', methods=['POST'])
def delete_definition(title, definition_id):
    body = request.get_json()
    try:
        word = db.session.query(Word).filter_by(title=title).one()
    except NoResultFound as ex:
        return jsonify({'error': 'Word does not exist'})

    posted_user_id = body.get('userId')
    if not posted_user_id:
        return jsonify({'error': 'User ID not supplied'})

    try:
        user = db.session.query(User).filter_by(twitter_id=posted_user_id).one()
    except NoResultFound as ex:
        return jsonify({'error': 'Auth Error'})

    posted_auth_token = body.get('authToken')
    token = encode_value(
        user.oauth_token,
        app.config.get('AUTH_SALT')
    )
    if token != posted_auth_token:
        return jsonify({'error': 'Auth Error'})

    try:
        definition = db.session.query(Definition).filter_by(id=definition_id).one()
    except NoResultFound as ex:
        return jsonify({'error': 'Definition does not exist'})

    db.session.delete(definition)
    db.session.commit()

    return jsonify({'deleted_definition': { 'id': definition_id}})


@app.route('/definition/<definition_id>/vote', methods=['POST'])
def vote(definition_id):
    body = request.get_json()

    try:
        definition = db.session.query(Definition).filter_by(id=definition_id).one()
    except NoResultFound as ex:
        return jsonify({'error': 'Definition does not exist'})

    try:
        user = db.session.query(User).filter_by(twitter_id=body.get('userId')).one()
    except NoResultFound as ex:
        return jsonify({'error': 'Auth Error'})

    posted_auth_token = body.get('authToken')
    token = encode_value(
        user.oauth_token,
        app.config.get('AUTH_SALT')
    )
    if token != posted_auth_token:
        return jsonify({'error': 'Auth Error'})

    try:
        vote = db.session.query(Vote).filter_by(definition_id=definition.id).\
                filter_by(user_id=user.id).one()
    except NoResultFound as ex:
        vote = Vote()
        vote.definition_id = definition.id
        vote.user_id = user.id

    vote.vote = 1 if body.get('isUpvote') else -1
    db.session.add(vote)
    db.session.commit()

    return jsonify({'vote': { 'id': vote.id}})

@app.route('/search/<term>', methods=['GET'])
def search(term):
    term_is_emoji = is_emoji(term)
    matching_words = []

    if term_is_emoji:
        try:
            match_object = db.session.query(Word).filter_by(title=term).one()
            exact_match = match_object.as_dict()
        except:
            exact_match = {
                'id': None,
                'title': term
            }

        matching_words = [exact_match]

        try:
            words = db.session.query(Word).filter(
                        Word.title.ilike('%{0}%'.format(term))
                    ).all()
            for word in words:
                if not exact_match or exact_match.id != word.id:
                    matching_words.append(word.as_dict())
        except:
            pass

    matching_definitions = []
    try:
        definitions = db.session.query(Definition).join(Word).\
                filter(Definition.definition.ilike('%{0}%'.format(term))).all()
        for definition in definitions:
            def_word = definition.word
            word_dict = def_word.as_dict()
            def_dict = definition.as_dict()
            def_dict['word'] = word_dict
            matching_definitions.append(def_dict)
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        eprint(exc_value)
        eprint(traceback.print_tb(exc_traceback))

    return jsonify({
        'isEmoji': term_is_emoji,
        'matchingWords': matching_words,
        'matchingDefinitions': matching_definitions
    })



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
    app.run(debug=True, host='0.0.0.0', threaded=True)
