import os
from pathlib import Path
from typing import List, Optional, Dict

from agno.utils.log import log_debug, log_error, log_info

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import Resource, build
    from googleapiclient.errors import HttpError
except ImportError:
    raise ImportError(
        "Bibliotecas do Google não encontradas. Instale com: "
        "`pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib`"
    )


class GoogleAuthManager:
    """
    Gerencia a autenticação OAuth 2.0 e a construção de serviços para as APIs do Google.
    Centraliza o fluxo de login para que o usuário se autentique apenas uma vez.
    """

    _creds: Optional[Credentials] = None
    _services: Dict[str, Resource] = {}

    def __init__(
        self,
        scopes: List[str],
        token_path: str = "google_token.json",
        credentials_path: str = "credentials.json",
        oauth_port: int = 8080,
    ):
        self.scopes = scopes
        self.token_path = token_path
        self.credentials_path = credentials_path
        self.oauth_port = oauth_port

    def _authenticate(self) -> None:
        """Garante que as credenciais sejam válidas, iniciando o fluxo de login se necessário."""
        if GoogleAuthManager._creds and GoogleAuthManager._creds.valid:
            return

        token_file = Path(self.token_path)
        if token_file.exists():
            GoogleAuthManager._creds = Credentials.from_authorized_user_file(str(token_file), self.scopes)

        if not GoogleAuthManager._creds or not GoogleAuthManager._creds.valid:
            if GoogleAuthManager._creds and GoogleAuthManager._creds.expired and GoogleAuthManager._creds.refresh_token:
                log_info("Atualizando token de acesso expirado...")
                GoogleAuthManager._creds.refresh(Request())
            else:
                log_info("Nenhum token válido encontrado. Iniciando novo fluxo de autenticação...")
                
                client_id = os.getenv("GOOGLE_CLIENT_ID")
                client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

                if not client_id or not client_secret:
                    error_msg = "As variáveis de ambiente GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET não foram encontradas. Verifique seu arquivo .env."
                    log_error(error_msg)
                    raise ValueError(error_msg)

                client_config = {
                    "installed": {
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                    }
                }
                flow = InstalledAppFlow.from_client_config(client_config, self.scopes)
                GoogleAuthManager._creds = flow.run_local_server(port=self.oauth_port)

            with open(token_file, "w") as token:
                token.write(GoogleAuthManager._creds.to_json())
            log_info(f"Token salvo com sucesso em: {token_file}")

    def get_service(self, api_name: str, api_version: str) -> Resource:
        """Retorna uma instância de serviço da API, autenticando se necessário."""
        service_key = f"{api_name}-{api_version}"
        if service_key in GoogleAuthManager._services:
            return GoogleAuthManager._services[service_key]

        self._authenticate()
        try:
            service = build(api_name, api_version, credentials=GoogleAuthManager._creds)
            GoogleAuthManager._services[service_key] = service
            return service
        except HttpError as error:
            log_error(f"Ocorreu um erro ao construir o serviço '{api_name}': {error}")
            raise ConnectionError(f"Falha ao construir o serviço da API do Google: {api_name}") from error