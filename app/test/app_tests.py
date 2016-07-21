import app
import test_utils

class AppTestCase(test_utils.AppBaseTestCase):

    def test_invalid_req(self):
        rv = self.app.get('/bad_url_dont_exist')
        assert rv.status_code == 404

    def test_index_exists(self):
        rv = self.app.get('/')
        assert rv.status_code == 200
        assert b'index' in rv.data

    def test_health(self):
        rv = self.app.get('/health')
        assert rv.status_code == 200
        assert b'OK' in rv.data
