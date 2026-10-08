"""
Regression tests for the Vercel Blob upload path.

Every other test runs without BLOB_READ_WRITE_TOKEN, so it only ever exercises
the local-disk branch of save_uploaded_file(). Production uses the Blob branch,
which therefore had zero coverage. These tests run the real vercel_blob.put()
against a mocked HTTP layer so we can assert on the request that actually goes
out - notably that `access: public` is sent - and on the URL handed back to the
admin UI.

Run:
    python -m pytest tests/ -v
"""
import io
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'jainzee-website'))

os.environ['ADMIN_PASSWORD'] = 'test-admin-pass-123'
os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-pytest-only')


@pytest.fixture()
def client(monkeypatch, tmp_path):
    tmpdir = str(tmp_path)
    db_path = os.path.join(tmpdir, 'test.db')
    upload_dir = os.path.join(tmpdir, 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    monkeypatch.setenv('JAINZEE_DB_PATH', db_path)
    # Neither backend may be pre-enabled by whatever ran before.
    monkeypatch.delenv('BLOB_READ_WRITE_TOKEN', raising=False)
    monkeypatch.delenv('VERCEL', raising=False)
    import importlib
    import app as app_module
    app_module = importlib.reload(app_module)
    app_module.app.config['TESTING'] = True  # disables CSRF for API tests
    app_module.app.config['UPLOAD_FOLDER'] = upload_dir
    with app_module.app.test_client() as c:
        yield app_module, c, upload_dir


def admin_login(c):
    r = c.post('/admin/login', data={'password': 'test-admin-pass-123'})
    assert r.status_code == 302, r.get_data(as_text=True)


def png_bytes():
    from PIL import Image
    buf = io.BytesIO()
    Image.new('RGB', (32, 32), (200, 30, 30)).save(buf, format='PNG')
    return buf.getvalue()


def upload_image(c, name='probe.png'):
    return c.post('/admin/api/upload',
                  data={'file': (io.BytesIO(png_bytes()), name)},
                  content_type='multipart/form-data')


# ---------------- VERCEL BLOB PATH ----------------

def test_blob_put_sends_public_access_and_returns_blob_url(client, monkeypatch):
    """The core contract: PUT to Blob with access=public, blob.url to the client."""
    app_module, c, upload_dir = client
    admin_login(c)

    import vercel_blob.blob_store as bs
    captured = {}

    def fake_request_factory(url, method, backoff_factor=0.5, timeout=10,
                             verbose=False, **kwargs):
        captured['url'] = url
        captured['method'] = method
        captured['headers'] = dict(kwargs.get('headers') or {})
        captured['data'] = kwargs.get('data')

        class FakeResp:
            status_code = 200

            def json(self):
                return {
                    'url': 'https://abc123.blob.vercel-storage.com/uploads/probe.png',
                    'pathname': 'uploads/probe.png',
                }
        return FakeResp()

    monkeypatch.setattr(bs, '_request_factory', fake_request_factory)
    monkeypatch.setattr(app_module, 'USE_BLOB_STORAGE', True)
    monkeypatch.setenv('BLOB_READ_WRITE_TOKEN', 'vercel_fake_token_for_test')

    before = set(os.listdir(upload_dir))
    r = upload_image(c)

    assert r.status_code == 200, r.get_data(as_text=True)
    # The admin UI reads exactly this field.
    assert r.get_json()['url'] == \
        'https://abc123.blob.vercel-storage.com/uploads/probe.png'

    headers = captured['headers']
    assert captured['method'] == 'PUT'
    # Vercel Blob has no private buckets; the SDK hardcodes this header, which is
    # what makes the returned URL publicly servable. Guard against it ever being
    # dropped or made non-public.
    assert headers['access'] == 'public'
    # addRandomSuffix keeps uploads from overwriting each other.
    assert headers.get('x-add-random-suffix') == '1'
    assert headers['authorization'].startswith('Bearer ')
    assert 'pathname=uploads/' in captured['url']
    assert captured['data'] == png_bytes()

    # On Vercel nothing may land on the (read-only) disk.
    assert set(os.listdir(upload_dir)) == before


def test_blob_branch_is_reported_by_upload_config(client, monkeypatch):
    app_module, c, _ = client
    admin_login(c)

    monkeypatch.setattr(app_module, 'USE_BLOB_STORAGE', True)
    assert c.get('/admin/api/upload-config').get_json()['blobEnabled'] is True

    monkeypatch.setattr(app_module, 'USE_BLOB_STORAGE', False)
    assert c.get('/admin/api/upload-config').get_json()['blobEnabled'] is False


def test_vercel_without_token_never_touches_disk(client, monkeypatch):
    """On Vercel with no token, fail with a readable 502 - and never write."""
    app_module, c, upload_dir = client
    admin_login(c)

    monkeypatch.setenv('VERCEL', '1')
    monkeypatch.delenv('BLOB_READ_WRITE_TOKEN', raising=False)
    monkeypatch.setattr(app_module, 'USE_BLOB_STORAGE', False)

    before = set(os.listdir(upload_dir))
    r = upload_image(c, name='whatsapp.jpg')

    assert r.status_code == 502, r.get_data(as_text=True)
    assert r.is_json, 'must be JSON so the admin UI can show the message'
    assert 'BLOB_READ_WRITE_TOKEN' in r.get_json()['error']
    assert set(os.listdir(upload_dir)) == before, 'disk must not be written to'


def test_vercel_without_token_is_not_a_bare_500(client, monkeypatch):
    """Regression: this used to surface as Flask's HTML 500 page."""
    app_module, c, _ = client
    admin_login(c)

    monkeypatch.setenv('VERCEL', '1')
    monkeypatch.delenv('BLOB_READ_WRITE_TOKEN', raising=False)
    monkeypatch.setattr(app_module, 'USE_BLOB_STORAGE', False)

    r = upload_image(c, name='whatsapp.jpg')
    assert r.status_code != 500
    assert r.content_type.startswith('application/json')


def test_local_upload_still_works_without_blob(client):
    """Development keeps working when no token is configured."""
    app_module, c, upload_dir = client
    admin_login(c)

    before = set(os.listdir(upload_dir))
    r = upload_image(c)

    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.get_json()['url'].startswith('/static/uploads/')
    assert len(set(os.listdir(upload_dir)) - before) == 1



