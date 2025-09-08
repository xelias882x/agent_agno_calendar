import base64
import datetime
import json
import os
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, List, Optional

from fastmcp import FastMCP

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    raise ImportError(
        "Bibliotecas do Google não encontradas. Instale com: "
        "`pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib`"
    )

# --- Configuração do Servidor MCP ---
mcp = FastMCP("Google API Tools Server")

# --- Gerenciamento Centralizado de Credenciais e Serviços ---

# Dicionário para armazenar serviços e credenciais já criados e evitar recriá-los.
_services = {}
_credentials = {}


def _get_google_credentials(
    scopes: List[str], token_filename: str, oauth_port: int = 8080
) -> Optional[Credentials]:
    """
    Função auxiliar para autenticar e obter credenciais do Google.
    Usa variáveis de ambiente para as credenciais do cliente OAuth.
    """
    if token_filename in _credentials and _credentials[token_filename].valid:
        return _credentials[token_filename]

    creds = None
    token_file = Path(token_filename)

    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Carrega a configuração do cliente a partir de variáveis de ambiente
            # ATENÇÃO: Configure estas variáveis no seu ambiente!
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
            if not all(client_config["installed"].values()):
                raise ValueError(
                    "Variáveis de ambiente (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, etc.) não estão configuradas."
                )

            flow = InstalledAppFlow.from_client_config(client_config, scopes)
            creds = flow.run_local_server(port=oauth_port)

    if creds:
        token_file.write_text(creds.to_json())
        _credentials[token_filename] = creds  # Armazena em cache

    return creds


def _get_service(api_name: str, api_version: str, scopes: List[str], token_filename: str):
    """Função auxiliar para construir um serviço da API do Google."""
    service_key = f"{api_name}-{api_version}"
    if service_key in _services:
        return _services[service_key]

    creds = _get_google_credentials(scopes, token_filename)
    if not creds:
        raise ConnectionError("Falha na autenticação com a API do Google.")

    try:
        service = build(api_name, api_version, credentials=creds)
        _services[service_key] = service  # Armazena em cache
        return service
    except HttpError as error:
        print(f"Ocorreu um erro ao construir o serviço '{api_name}': {error}")
        return None


# --- Ferramentas do Google Calendar ---

CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]
CALENDAR_TOKEN = "calendar_token.json"


@mcp.tool
def list_calendar_events(limit: int = 10) -> str:
    """Lista os próximos eventos do Google Calendar."""
    try:
        service = _get_service("calendar", "v3", CALENDAR_SCOPES, CALENDAR_TOKEN)
        now = datetime.datetime.utcnow().isoformat() + "Z"
        events_result = service.events().list(
            calendarId="primary", timeMin=now, maxResults=limit, singleEvents=True, orderBy="startTime"
        ).execute()
        events = events_result.get("items", [])
        if not events:
            return "Nenhum compromisso futuro encontrado."
        return json.dumps(events, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Ocorreu um erro: {e}"})

@mcp.tool
def create_calendar_event(summary: str, start_time: str, end_time: str, description: Optional[str] = None, location: Optional[str] = None) -> str:
    """
    Cria um novo evento no Google Calendar. As datas e horas devem estar no formato ISO 8601 (ex: '2024-09-15T10:00:00-03:00').
    """
    try:
        service = _get_service("calendar", "v3", CALENDAR_SCOPES, CALENDAR_TOKEN)
        event = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': {'dateTime': start_time, 'timeZone': 'America/Sao_Paulo'},
            'end': {'dateTime': end_time, 'timeZone': 'America/Sao_Paulo'},
        }
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        return json.dumps(created_event)
    except Exception as e:
        return json.dumps({"error": f"Ocorreu um erro ao criar o evento: {e}"})

@mcp.tool
def update_calendar_event(event_id: str, summary: Optional[str] = None, start_time: Optional[str] = None, end_time: Optional[str] = None, description: Optional[str] = None, location: Optional[str] = None) -> str:
    """
    Atualiza um evento existente no Google Calendar usando seu ID. Apenas os campos fornecidos serão atualizados.
    """
    try:
        service = _get_service("calendar", "v3", CALENDAR_SCOPES, CALENDAR_TOKEN)
        event = service.events().get(calendarId='primary', eventId=event_id).execute()
        
        if summary: event['summary'] = summary
        if location: event['location'] = location
        if description: event['description'] = description
        if start_time: event['start']['dateTime'] = start_time
        if end_time: event['end']['dateTime'] = end_time

        updated_event = service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
        return json.dumps(updated_event)
    except Exception as e:
        return json.dumps({"error": f"Ocorreu um erro ao atualizar o evento: {e}"})

@mcp.tool
def delete_calendar_event(event_id: str) -> str:
    """
    Exclui um evento do Google Calendar usando seu ID.
    """
    try:
        service = _get_service("calendar", "v3", CALENDAR_SCOPES, CALENDAR_TOKEN)
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return json.dumps({"message": f"Evento com ID {event_id} foi excluído com sucesso."})
    except Exception as e:
        return json.dumps({"error": f"Ocorreu um erro ao excluir o evento: {e}"})


# --- Ferramentas do Google Gmail ---

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]
GMAIL_TOKEN = "gmail_token.json"


@mcp.tool
def search_emails(query: str, max_results: int = 10) -> str:
    """Busca por emails no Gmail que correspondam a uma consulta."""
    try:
        service = _get_service("gmail", "v1", GMAIL_SCOPES, GMAIL_TOKEN)
        result = service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()
        messages = result.get("messages", [])
        if not messages:
            return json.dumps({"message": "Nenhum email encontrado."})
        return json.dumps(messages)
    except Exception as e:
        return json.dumps({"error": f"Ocorreu um erro: {e}"})


@mcp.tool
def get_email_details(message_id: str) -> str:
    """Obtém os detalhes completos de um email específico pelo seu ID."""
    try:
        service = _get_service("gmail", "v1", GMAIL_SCOPES, GMAIL_TOKEN)
        message = service.users().messages().get(userId="me", id=message_id).execute()
        return json.dumps(message)
    except Exception as e:
        return json.dumps({"error": f"Ocorreu um erro: {e}"})


@mcp.tool
def send_email(to: str, subject: str, body: str) -> str:
    """Envia um email a partir da conta do usuário autenticado."""
    try:
        service = _get_service("gmail", "v1", GMAIL_SCOPES, GMAIL_TOKEN)
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {"raw": raw_message}
        sent_message = service.users().messages().send(
            userId="me", body=create_message
        ).execute()
        return json.dumps(sent_message)
    except Exception as e:
        return json.dumps({"error": f"Ocorreu um erro: {e}"})


# --- Ferramentas do Google Sheets ---

SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SHEETS_TOKEN = "sheets_token.json"


@mcp.tool
def get_spreadsheet_data(spreadsheet_id: str, range_name: str) -> str:
    """Obtém dados de uma planilha do Google Sheets."""
    try:
        service = _get_service("sheets", "v4", SHEETS_SCOPES, SHEETS_TOKEN)
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=range_name
        ).execute()
        values = result.get("values", [])
        if not values:
            return json.dumps({"message": "Nenhum dado encontrado."})
        return json.dumps(values)
    except Exception as e:
        return json.dumps({"error": f"Ocorreu um erro: {e}"})


@mcp.tool
def update_spreadsheet_data(
    spreadsheet_id: str, range_name: str, values: List[List[Any]]
) -> str:
    """Atualiza dados em uma planilha do Google Sheets."""
    try:
        service = _get_service("sheets", "v4", SHEETS_SCOPES, SHEETS_TOKEN)
        body = {"values": values}
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="USER_ENTERED",
            body=body,
        ).execute()
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": f"Ocorreu um erro: {e}"})

@mcp.tool
def append_spreadsheet_data(spreadsheet_id: str, range_name: str, values: List[List[Any]]) -> str:
    """
    Adiciona dados ao final de uma tabela em uma planilha do Google Sheets.
    """
    try:
        service = _get_service("sheets", "v4", SHEETS_SCOPES, SHEETS_TOKEN)
        body = {"values": values}
        result = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body,
        ).execute()
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": f"Ocorreu um erro ao adicionar dados: {e}"})


if __name__ == "__main__":
    print("Servidor de ferramentas Google API pronto para ser iniciado.")
    print("Use o comando: fastmcp run tools_google_api.py --transport http --port 8001")
    # Para iniciar o servidor, você precisa executar o comando acima no terminal.
    # A linha abaixo iniciaria o servidor em modo stdio, que não é o desejado.
    # mcp.run()

    # Lembre-se de configurar as variáveis de ambiente antes de rodar:
    # GOOGLE_CLIENT_ID
    # GOOGLE_CLIENT_SECRET
    # GOOGLE_PROJECT_ID
    # GOOGLE_REDIRECT_URI (opcional, padrão: http://localhost)