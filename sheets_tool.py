import json
import os
from functools import wraps
from pathlib import Path
from typing import Any, List, Optional

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
                self.service = build("sheets", "v4", credentials=self.creds)
        except Exception as e:
            log_error(f"An error occurred during authentication: {e}")
            return json.dumps({"error": f"Authentication failed: {e}"})
        return func(self, *args, **kwargs)

    return wrapper


class GoogleSheetsTool(Toolkit):
    DEFAULT_SCOPES = {
        "read": "https://www.googleapis.com/auth/spreadsheets.readonly",
        "write": "https://www.googleapis.com/auth/spreadsheets",
    }
    service: Optional[Resource]

    def __init__(
        self,
        scopes: Optional[List[str]] = None,
        credentials_path: Optional[str] = None,
        token_path: Optional[str] = "sheets_token.json",
        oauth_port: int = 8080,
        allow_update: bool = True,
        **kwargs,
    ):
        self.creds: Optional[Credentials] = None
        self.service: Optional[Resource] = None
        self.oauth_port: int = oauth_port
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.allow_update = allow_update
        self.scopes = scopes or []

        if not self.scopes:
            self.scopes.append(self.DEFAULT_SCOPES["read"])
            if self.allow_update:
                self.scopes.append(self.DEFAULT_SCOPES["write"])

        if self.allow_update and self.DEFAULT_SCOPES["write"] not in self.scopes:
            raise ValueError(f"The scope {self.DEFAULT_SCOPES['write']} is required for write operations")
        if self.DEFAULT_SCOPES["read"] not in self.scopes and self.DEFAULT_SCOPES["write"] not in self.scopes:
            raise ValueError(
                f"Either {self.DEFAULT_SCOPES['read']} or {self.DEFAULT_SCOPES['write']} is required for read operations"
            )

        super().__init__(
            name="google_sheets_tool",
            tools=[
                self.get_spreadsheet_data,
                self.update_spreadsheet_data,
                self.append_spreadsheet_data,
                self.create_spreadsheet,
            ],
            **kwargs,
        )

    def _auth(self) -> None:
        """
        Authenticate with Google Sheets API
        """
        if self.creds and self.creds.valid:
            return

        token_file = Path(self.token_path or "sheets_token.json")
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
            log_debug("Successfully authenticated with Google Sheets API.")
            log_info(f"Token file path: {token_file}")

    @authenticate
    def create_spreadsheet(self, title: str) -> str:
        """
        Creates a new Google Spreadsheet.

        Args:
            title (str): The title of the spreadsheet.

        Returns:
            str: JSON string containing the created spreadsheet's properties or an error message.
        """
        try:
            spreadsheet = {"properties": {"title": title}}
            spreadsheet = (
                self.service.spreadsheets()  # type: ignore
                .create(body=spreadsheet, fields="spreadsheetId,properties.title,spreadsheetUrl")
                .execute()
            )
            log_info(f"Spreadsheet created: {spreadsheet.get('spreadsheetUrl')}")
            return json.dumps(spreadsheet)
        except HttpError as error:
            log_error(f"An error occurred: {error}")
            return json.dumps({"error": f"An error occurred: {error}"})

    @authenticate
    def get_spreadsheet_data(self, spreadsheet_id: str, range_name: str) -> str:
        """
        Gets data from a Google Spreadsheet.

        Args:
            spreadsheet_id (str): The ID of the spreadsheet.
            range_name (str): The A1 notation of the range to retrieve. E.g., 'Sheet1!A1:B2'.

        Returns:
            str: JSON string containing the spreadsheet data or an error message.
        """
        try:
            result = (
                self.service.spreadsheets()  # type: ignore
                .values()
                .get(spreadsheetId=spreadsheet_id, range=range_name)
                .execute()
            )
            values = result.get("values", [])
            if not values:
                return json.dumps({"message": "No data found."})
            return json.dumps(values)
        except HttpError as error:
            log_error(f"An error occurred: {error}")
            return json.dumps({"error": f"An error occurred: {error}"})

    @authenticate
    def update_spreadsheet_data(self, spreadsheet_id: str, range_name: str, values: List[List[Any]]) -> str:
        """
        Updates data in a Google Spreadsheet.

        Args:
            spreadsheet_id (str): The ID of the spreadsheet.
            range_name (str): The A1 notation of the range to update. E.g., 'Sheet1!A1'.
            values (List[List[Any]]): The data to be written. This is a list of lists, where each inner list represents a row.

        Returns:
            str: JSON string containing the update response or an error message.
        """
        try:
            body = {"values": values}
            result = (
                self.service.spreadsheets()  # type: ignore
                .values()
                .update(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueInputOption="USER_ENTERED",
                    body=body,
                )
                .execute()
            )
            log_info(f"{result.get('updatedCells')} cells updated.")
            return json.dumps(result)
        except HttpError as error:
            log_error(f"An error occurred: {error}")
            return json.dumps({"error": f"An error occurred: {error}"})

    @authenticate
    def append_spreadsheet_data(self, spreadsheet_id: str, range_name: str, values: List[List[Any]]) -> str:
        """
        Appends data to a Google Spreadsheet.

        Args:
            spreadsheet_id (str): The ID of the spreadsheet.
            range_name (str): The A1 notation of a range to search for a table, after which the values will be appended. E.g., 'Sheet1!A1'.
            values (List[List[Any]]): The data to be appended. This is a list of lists, where each inner list represents a row.

        Returns:
            str: JSON string containing the append response or an error message.
        """
        try:
            body = {"values": values}
            result = (
                self.service.spreadsheets()  # type: ignore
                .values()
                .append(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueInputOption="USER_ENTERED",
                    insertDataOption="INSERT_ROWS",
                    body=body,
                )
                .execute()
            )
            log_info(f"Appended data to spreadsheet: {spreadsheet_id}")
            return json.dumps(result)
        except HttpError as error:
            log_error(f"An error occurred: {error}")
            return json.dumps({"error": f"An error occurred: {error}"})