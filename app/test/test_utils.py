import unittest

import app

def save_and_refresh(session, record):
    session.add(record)
    app.db.session.commit()
    record_id = record.id
    session.expunge_all()
    return session.query(type(record)).filter_by(id=record_id).one()

def save(session, record):
    session.add(record)
    app.db.session.commit()
    return record


class AppBaseTestCase(unittest.TestCase):

    def setUp(self):
        app.app.config['TESTING'] = True
        app.app.config['SQLALCHEMY_DATABASE_URI']=\
            '{}/test'.format(app.db_uri)
        self.app = app.app.test_client()
        with app.app.app_context():
            app.create_tables()

    def tearDown(self):
        with app.app.app_context():
            app.drop_tables()
