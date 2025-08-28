import datetime
import os.path
from typing import List, Optional
 
from agno.tools import Toolkit
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Se modificar esses escopos, delete o arquivo token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

class GoogleCalendarTool(Toolkit):
    """Um toolkit para interagir com a API do Google Calendar."""

    def __init__(self, **kwargs):
        """Inicializa a ferramenta e autentica com a API do Google Calendar."""
        creds = self._get_credentials()
        self.service = build("calendar", "v3", credentials=creds)
        print("Ferramenta Google Calendar conectada com sucesso.")
        # Registra os métodos decorados como ferramentas para este toolkit.
        # Adicionamos as novas ferramentas de CRUD aqui.
        super().__init__(
            name="GoogleCalendarTool",
            tools=[self.list_events, self.create_event, self.update_event, self.delete_event],
            **kwargs
        )

    def _get_credentials(self):
        """Obtém as credenciais do usuário, lidando com o fluxo de autenticação."""
        creds = None
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
                creds = flow.run_local_server(port=0)
            with open("token.json", "w") as token:
                token.write(creds.to_json())
        return creds

    def list_events(self, limit: int = 10) -> str:
        """
        Busca e lista os próximos eventos da agenda do Google Calendar do usuário.
        Use esta ferramenta sempre que o usuário perguntar sobre seus compromissos,
        agenda, eventos futuros ou o que ele tem para fazer.
 
        Args:
            limit (int): O número máximo de eventos a serem retornados. O padrão é 10.
 
        Returns:
            Uma string formatada com a lista dos próximos eventos, incluindo o ID de cada evento,
            ou uma mensagem indicando que não há eventos.
        """
        try:
            now = datetime.datetime.utcnow().isoformat() + "Z"  # 'Z' indica UTC
            events_result = self.service.events().list(calendarId="primary", timeMin=now, maxResults=limit, singleEvents=True, orderBy="startTime").execute()
            events = events_result.get("items", [])
 
            if not events:
                return "Nenhum compromisso encontrado."
 
            event_list = [f"- ID: {event['id']}, Início: {event['start'].get('dateTime', event['start'].get('date'))}, Título: {event['summary']}" for event in events]
            return "Seus próximos compromissos são:\n" + "\n".join(event_list)
        except HttpError as error:
            return f"Ocorreu um erro na API do Google Calendar: {error}"
        except Exception as e:
            return f"Ocorreu um erro inesperado: {e}"

    def create_event(self, summary: str, start_time: str, end_time: str, description: Optional[str] = None, location: Optional[str] = None) -> str:
        """
        Cria um novo evento no Google Calendar. As datas e horas devem estar no formato ISO 8601 (ex: '2024-09-15T10:00:00-03:00').

        Args:
            summary (str): O título ou resumo do evento.
            start_time (str): A data e hora de início do evento no formato ISO 8601.
            end_time (str): A data e hora de término do evento no formato ISO 8601.
            description (Optional[str]): Uma descrição detalhada do evento.
            location (Optional[str]): O local do evento.

        Returns:
            Uma mensagem de confirmação com o link para o evento criado ou uma mensagem de erro.
        """
        try:
            event = {
                'summary': summary,
                'location': location,
                'description': description,
                'start': {'dateTime': start_time},
                'end': {'dateTime': end_time},
            }
            created_event = self.service.events().insert(calendarId='primary', body=event).execute()
            return f"Evento criado com sucesso! Link: {created_event.get('htmlLink')}"
        except HttpError as error:
            return f"Ocorreu um erro ao criar o evento: {error}"
        except Exception as e:
            return f"Ocorreu um erro inesperado ao criar o evento: {e}"

    def update_event(self, event_id: str, summary: Optional[str] = None, start_time: Optional[str] = None, end_time: Optional[str] = None, description: Optional[str] = None, location: Optional[str] = None) -> str:
        """
        Atualiza um evento existente no Google Calendar usando seu ID. Apenas os campos fornecidos serão atualizados.

        Args:
            event_id (str): O ID do evento a ser atualizado. Use a ferramenta list_events para encontrar o ID.
            summary (Optional[str]): O novo título para o evento.
            start_time (Optional[str]): A nova data e hora de início no formato ISO 8601.
            end_time (Optional[str]): A nova data e hora de término no formato ISO 8601.
            description (Optional[str]): A nova descrição para o evento.
            location (Optional[str]): O novo local para o evento.

        Returns:
            Uma mensagem de confirmação ou uma mensagem de erro.
        """
        try:
            event = self.service.events().get(calendarId='primary', eventId=event_id).execute()
            if summary: event['summary'] = summary
            if location: event['location'] = location
            if description: event['description'] = description
            if start_time: event['start']['dateTime'] = start_time
            if end_time: event['end']['dateTime'] = end_time
            updated_event = self.service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
            return f"Evento '{updated_event.get('summary')}' atualizado com sucesso."
        except HttpError as error:
            return f"Ocorreu um erro ao atualizar o evento: {error}"

    def delete_event(self, event_id: str) -> str:
        """
        Exclui um evento do Google Calendar usando seu ID.

        Args:
            event_id (str): O ID do evento a ser excluído. Use a ferramenta list_events para encontrar o ID.

        Returns:
            Uma mensagem de confirmação ou uma mensagem de erro.
        """
        try:
            self.service.events().delete(calendarId='primary', eventId=event_id).execute()
            return f"Evento com ID {event_id} foi excluído com sucesso."
        except HttpError as error:
            return f"Ocorreu um erro ao excluir o evento: {error}"