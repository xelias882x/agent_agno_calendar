import datetime
from typing import Any, List, Optional

from langchain_core.tools import tool, StructuredTool
from agno.utils.log import log_info

try:
    from googleapiclient.errors import HttpError
except ImportError:
    raise ImportError(
        "Google client libraries not found, Please install using `pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib`"
    )

from google_auth import GoogleAuthManager


class GoogleCalendarTool:
    """Um toolkit para interagir com a API do Google Calendar."""

    SCOPES = ["https://www.googleapis.com/auth/calendar"]

    def __init__(self, auth_manager: GoogleAuthManager):
        self.auth_manager = auth_manager
        log_info("Ferramenta Google Calendar conectada com sucesso.")

    def get_tools(self) -> List[Any]:
        """Retorna uma lista de todas as ferramentas disponíveis neste toolkit."""
        return [
            StructuredTool.from_function(self.list_events),
            StructuredTool.from_function(self.create_event),
            StructuredTool.from_function(self.update_event),
            StructuredTool.from_function(self.delete_event),
        ]

    def service(self):
        """Método auxiliar para obter o serviço autenticado da API."""
        return self.auth_manager.get_service("calendar", "v3")

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
            events_result = self.service().events().list(calendarId="primary", timeMin=now, maxResults=limit, singleEvents=True, orderBy="startTime").execute()
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
            created_event = self.service().events().insert(calendarId='primary', body=event).execute()
            return f"Evento criado com sucesso! Link: {created_event.get('htmlLink')}"
        except HttpError as error:
            return f"Ocorreu um erro ao criar o evento: {error}"
        except Exception as e:
            return f"Ocorreu um erro inesperado ao criar o evento: {e}"

    def update_event(self, event_id: str, summary: Optional[str] = None, start_time: Optional[str] = None, end_time: Optional[str] = None, description: Optional[str] = None, location: Optional[str] = None) -> str:
        """
        Atualiza um evento existente no Google Calendar usando seu ID. Apenas os campos fornecidos serão atualizados.
        Se apenas a hora for fornecida para start_time ou end_time (ex: '13:00'), a data original do evento será mantida.

        Args:
            event_id (str): O ID do evento a ser atualizado. Use a ferramenta list_events para encontrar o ID.
            summary (Optional[str]): O novo título para o evento.
            start_time (Optional[str]): A nova data e hora de início (formato ISO 8601) ou apenas a nova hora (ex: '14:30').
            end_time (Optional[str]): A nova data e hora de término (formato ISO 8601) ou apenas a nova hora (ex: '15:00').
            description (Optional[str]): A nova descrição para o evento.
            location (Optional[str]): O novo local para o evento.

        Returns:
            Uma mensagem de confirmação ou uma mensagem de erro.
        """
        try:
            event = self.service().events().get(calendarId='primary', eventId=event_id).execute()
            
            # Lógica para combinar a data existente com a nova hora, se necessário
            def get_full_datetime(new_time_str: Optional[str], original_datetime_str: str) -> Optional[str]:
                if not new_time_str:
                    return None
                try:
                    # Se o usuário já passou a data completa, use-a
                    datetime.datetime.fromisoformat(new_time_str)
                    return new_time_str
                except ValueError:
                    # Se for apenas a hora (ex: "13:00"), combine com a data original
                    original_date = datetime.datetime.fromisoformat(original_datetime_str).date()
                    new_time = datetime.time.fromisoformat(new_time_str)
                    return datetime.datetime.combine(original_date, new_time).isoformat()

            if summary: event['summary'] = summary
            if location: event['location'] = location
            if description: event['description'] = description
            
            new_start = get_full_datetime(start_time, event['start'].get('dateTime'))
            if new_start: event['start']['dateTime'] = new_start

            new_end = get_full_datetime(end_time, event['end'].get('dateTime'))
            if new_end: event['end']['dateTime'] = new_end

            updated_event = self.service().events().update(calendarId='primary', eventId=event_id, body=event).execute()
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
            self.service().events().delete(calendarId='primary', eventId=event_id).execute()
            return f"Evento com ID {event_id} foi excluído com sucesso."
        except HttpError as error:
            return f"Ocorreu um erro ao excluir o evento: {error}"