
import os
import json
import pickle
import logging

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import AuthorizedSession
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

DEFAULT_SCOPES=[
    'https://www.googleapis.com/auth/photoslibrary',
    #'https://www.googleapis.com/auth/photoslibrary.sharing',
]

AUTH_TOKENS = "auth.token"
UPLOAD_API = 'https://photoslibrary.googleapis.com/v1/mediaItems:batchCreate'
ALBUMS_API = 'https://photoslibrary.googleapis.com/v1/albums'

class GooglePhotos(object):

    def __init__(self, secret):
        self.credentials = self.authenticate(secret, DEFAULT_SCOPES)

    @property
    def credentials(self):
        self.refresh()
        
        return self._creds
     
    @credentials.setter
    def credentials(self, creds):
        self._creds = creds

    @property
    def session(self):
        '''
        returns a new session
        '''
        return AuthorizedSession(self.credentials)

    def refresh(self):
        if self._creds.expired and self._creds.refresh_token:
            self._creds.refresh(Request())

    def authenticate(self, secrets, scopes):
        credentials = None
        secrets_dir = os.path.dirname(os.path.abspath(secrets))
        token_path = os.path.join(secrets_dir, AUTH_TOKENS)

        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                credentials = pickle.load(token)

        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                app_flow = InstalledAppFlow.from_client_secrets_file(
                    secrets, scopes)
                credentials = app_flow.run_local_server(host='localhost',
                                                        open_browser=False)

            with open(token_path, 'wb') as token:
                pickle.dump(credentials, token)
        
        return credentials

    def get_albums(self):
        albums = self.session.get(ALBUMS_API).json()

        id_mapper = {}

        # no albums key if no albums
        for album in albums.get('albums', []): 
            id_mapper[album['title']] = album['id']

        return id_mapper

    def create_album(self, album):
        body = json.dumps({"album":{"title": album}})
        resp = self.session.post(ALBUMS_API, body).json()

        logger.debug("Server response: {}".format(resp))

        if "id" in resp:
            logger.info('Created new album: %s -> %s' % (album, resp['id']))
            return resp['id']
        else:
            logger.error("Could not create album %s" % album)
            logger.error(resp)
            raise Exception('Cannot create album %s' % album)

    def upload_photo(self, album, filename, stream):
        # grab a nenw session
        session = self.session

        session.headers["Content-type"] = "application/octet-stream"
        session.headers["X-Goog-Upload-Protocol"] = "raw"
        session.headers["X-Goog-Upload-File-Name"] = filename

        logger.info("Uploading %s" % filename)

        # google requires you to upload a token first, then create media from token
        token = session.post('https://photoslibrary.googleapis.com/v1/uploads', 
                            stream.read())

        if token.status_code == 200 and token.content:

            body = {"albumId": album, 
                    "newMediaItems": [
                        {"description":"",
                        "simpleMediaItem": {
                            "fileName": filename,
                            "uploadToken": token.content.decode()
                        }}
                    ]}

            resp = session.post(UPLOAD_API, json.dumps(body, indent=4)).json()

            logger.debug("Server response: {}".format(resp))

            if "newMediaItemResults" in resp:
                status = resp["newMediaItemResults"][0]["status"]
                if status.get("code") and (status.get("code") > 0):
                    logger.error("Could not upload %s to library" % filename)
                    logger.error('Error: %s' % status["message"])
                else:
                    logger.info("Added %s to library" % filename)
            else:
                logger.error("Could not add %s to library." % filename)
                logger.error("Server Response: %s" % resp)

        else:
            logger.error("Server Response: %s" % token)

if __name__ == '__main__':
    obj = GooglePhotos('client_secret.json')
    import pdb; pdb.set_trace()