from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

db_uri = 'postgresql+psycopg2://postgres:postgres@postgres:5432'
engine = create_engine(db_uri+'/template1')

def create_dbs():
    create_db_if_not_exists('test')
    create_db_if_not_exists('dev')
    return 'created dbs'

def create_db_if_not_exists(db_name):
    result = engine.execute(
            "SELECT 1 FROM pg_database WHERE datname = '{}'".format(db_name))
    res = []
    for row in result:
        res.append(row[0])
    if not res:
        create_db(db_name)

def create_db(db_name):
    session = sessionmaker(bind=engine)()
    session.connection().connection.set_isolation_level(0)
    session.execute('CREATE DATABASE {}'.format(db_name))
    session.connection().connection.set_isolation_level(1)
    session.close()


if __name__ == '__main__':
    create_dbs()
