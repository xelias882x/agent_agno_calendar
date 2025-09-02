import base64
import json
import os
from email.mime.text import MIMEText
from functools import wraps
from pathlib import Path
from typing import List, Optional

from agno.tools import Toolkit
from agno.utils.log import log_debug, log_error, log_info

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import Resource, build
    from googleapiclient.errors import HttpError

except ImportError:
    raise ImportError(
        "Google client libraries not found, Please install using `pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib`"
    )


def authenticate(func):
    """Decorator to ensure authentication before executing the method."""

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            if not self.creds or not self.creds.valid:
                self._auth()
            if not self.service:
                self.service = build("gmail", "v1", credentials=self.creds)
        except Exception as e:
            log_error(f"An error occurred during authentication: {e}")
            return json.dumps({"error": f"Authentication failed: {e}"})
        return func(self, *args, **kwargs)

    return wrapper


class GoogleGmailTool(Toolkit):
    DEFAULT_SCOPES = {
        "read": "https://www.googleapis.com/auth/gmail.readonly",
        "send": "https://www.googleapis.com/auth/gmail.send",
    }
    service: Optional[Resource]

    def __init__(
        self,
        scopes: Optional[List[str]] = None,
        credentials_path: Optional[str] = None,
        token_path: Optional[str] = "gmail_token.json",
        oauth_port: int = 8080,
        allow_send: bool = True,
        **kwargs,
    ):
        self.creds: Optional[Credentials] = None
        self.service: Optional[Resource] = None
        self.oauth_port: int = oauth_port
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.allow_send = allow_send
        self.scopes = scopes or []

        if not self.scopes:
            self.scopes.append(self.DEFAULT_SCOPES["read"])
            if self.allow_send:
                self.scopes.append(self.DEFAULT_SCOPES["send"])

        if self.allow_send and self.DEFAULT_SCOPES["send"] not in self.scopes:
            raise ValueError(f"The scope {self.DEFAULT_SCOPES['send']} is required for sending emails.")
        if self.DEFAULT_SCOPES["read"] not in self.scopes:
            raise ValueError(f"The scope {self.DEFAULT_SCOPES['read']} is required for reading emails.")

        tools_to_register = [self.search_emails, self.get_email_details]
        if self.allow_send:
            tools_to_register.append(self.send_email)

        super().__init__(
            name="GoogleGmailTool",
            tools=tools_to_register,
            **kwargs,
        )

    def _auth(self) -> None:
        """Authenticate with Gmail API"""
        if self.creds and self.creds.valid:
            return

        token_file = Path(self.token_path or "gmail_token.json")
        creds_file = Path(self.credentials_path or "credentials.json")

        if token_file.exists():
            self.creds = Credentials.from_authorized_user_file(str(token_file), self.scopes)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                client_config = {
                    "installed": {
                        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                        "project_id": os.getenv("GOOGLE_PROJECT_ID"),
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                        "redirect_uris": [os.getenv("GOOGLE_REDIRECT_URI", "http://localhost")],
                    }
                } 
                if creds_file.exists():
                    flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), self.scopes)
                else:
                    flow = InstalledAppFlow.from_client_config(client_config, self.scopes)
                self.creds = flow.run_local_server(port=self.oauth_port)

        if self.creds:
            token_file.write_text(self.creds.to_json())
            log_debug("Successfully authenticated with Gmail API.")
            log_info(f"Token file path: {token_file}")

    @authenticate
    def search_emails(self, query: str, max_results: int = 10) -> str:
        """Searches for emails matching a specific query."""
        try:
            result = self.service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()  # type: ignore
            messages = result.get("messages", [])
            if not messages:
                return json.dumps({"message": "No emails found."})
            return json.dumps(messages)
        except HttpError as error:
            return json.dumps({"error": f"An error occurred: {error}"})

    @authenticate
    def get_email_details(self, message_id: str) -> str:
        """Gets the full details of a specific email message."""
        try:
            message = self.service.users().messages().get(userId="me", id=message_id).execute()  # type: ignore
            return json.dumps(message)
        except HttpError as error:
            return json.dumps({"error": f"An error occurred: {error}"})

    @authenticate
    def send_email(self, to: str, subject: str, body: str) -> str:
        """Sends an email from the authenticated user's account."""
        try:
            message = MIMEText(body)
            message["to"] = to
            message["subject"] = subject
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            create_message = {"raw": raw_message}
            sent_message = self.service.users().messages().send(userId="me", body=create_message).execute()  # type: ignore
            return json.dumps(sent_message)
        except HttpError as error:
            return json.dumps({"error": f"An error occurred: {error}"})