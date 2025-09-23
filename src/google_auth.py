# google_auth.py
import pickle
import os.path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

class GoogleAuth:
    """
    Manages Google API authentication.
    """
    def __init__(self, scopes, credentials_file='credentials.json', token_file='token.pickle'):
        self.scopes = scopes
        self.credentials_file = credentials_file
        self.token_file = token_file

    def get_credentials(self):
        """
        Manages Google API authentication. It will either load saved credentials,
        refresh expired ones, or prompt the user to log in for the first time.
        
        Returns:
            google.oauth2.credentials.Credentials: Valid credentials for the Google API.
        """
        creds = None
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, self.scopes)
                creds = flow.run_local_server(port=0)
            
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
        return creds
