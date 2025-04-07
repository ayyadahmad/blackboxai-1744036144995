#!/usr/bin/env python3

import os
import pickle
import yaml
import keyring
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

class DriveAuth:
    """Handles Google Drive API authentication and credential management."""
    
    def __init__(self, config_path='config.yaml'):
        """Initialize the authenticator with configuration."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.credentials_file = self.config['google_api']['credentials_file']
        self.scopes = self.config['google_api']['scopes']
        self.keyring_service = self.config['security']['keyring_service_name']
        self.keyring_username = self.config['security']['keyring_username']

    def get_credentials(self):
        """
        Get valid credentials for Google Drive API access.
        
        Returns:
            google.oauth2.credentials.Credentials: Valid credentials object
        
        The function will:
        1. Check for stored credentials in keyring
        2. If stored credentials exist and are valid, use them
        3. If stored credentials are expired, refresh them
        4. If no valid credentials exist, run the OAuth2 flow
        """
        creds = None
        stored_token = keyring.get_password(self.keyring_service, self.keyring_username)
        
        if stored_token:
            try:
                creds = pickle.loads(stored_token)
            except Exception:
                # If there's any error unpickling, treat as no credentials
                pass

        # If credentials don't exist or are invalid
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    # If refresh fails, we'll need new credentials
                    creds = None
            
            # If we still don't have valid credentials, run the OAuth flow
            if not creds:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(
                        f"Credentials file '{self.credentials_file}' not found. "
                        "Please download it from Google Cloud Console."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.scopes)
                creds = flow.run_local_server(port=0)

            # Save the credentials
            token_pickle = pickle.dumps(creds)
            keyring.set_password(self.keyring_service, self.keyring_username, token_pickle)

        return creds

    def get_service(self):
        """
        Build and return an authorized Drive API service instance.
        
        Returns:
            googleapiclient.discovery.Resource: Authorized Drive API service instance
        """
        creds = self.get_credentials()
        service = build('drive', 'v3', credentials=creds)
        return service

    def revoke_credentials(self):
        """
        Revoke the current credentials and remove them from storage.
        Useful for testing or when permissions need to be reset.
        """
        stored_token = keyring.get_password(self.keyring_service, self.keyring_username)
        if stored_token:
            try:
                creds = pickle.loads(stored_token)
                if creds:
                    creds.revoke(Request())
            except Exception:
                pass  # Best effort to revoke
            finally:
                keyring.delete_password(self.keyring_service, self.keyring_username)

def test_auth():
    """
    Test function to verify authentication is working.
    """
    try:
        auth = DriveAuth()
        service = auth.get_service()
        # Test API call
        results = service.files().list(pageSize=1).execute()
        print("Authentication successful!")
        return True
    except Exception as e:
        print(f"Authentication failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_auth()