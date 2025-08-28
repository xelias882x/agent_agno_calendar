from __future__ import print_function

import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# O escopo foi alterado para permitir leitura e escrita.
# Se você modificar os escopos, apague o arquivo token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']
CREDENTIALS_FILE = 'credenciais_calendar.json'
TOKEN_FILE = 'token.json'

def get_calendar_service():
    """Autentica e retorna uma instância de serviço da API do Google Calendar."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Apague o token.json se mudar o SCOPES
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('calendar', 'v3', credentials=creds)
        print("Serviço do Google Calendar criado com sucesso.")
        return service
    except HttpError as error:
        print(f'Ocorreu um erro ao criar o serviço: {error}')
        return None

def list_upcoming_events(service, max_results=10):
    """Lista os próximos eventos e seus IDs."""
    # A linha abaixo foi substituída para corrigir o DeprecationWarning
    # e usar o método moderno para obter o tempo em UTC.
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    print(f'Buscando os próximos {max_results} eventos...')
    try:
        events_result = service.events().list(
            calendarId='primary', timeMin=now,
            maxResults=max_results, singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])

        if not events:
            print('Nenhum evento futuro encontrado.')
            return []

        print("Eventos futuros:")
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            print(f"- {start} | {event['summary']} (ID: {event['id']})")
        return events
    except HttpError as error:
        print(f'Ocorreu um erro ao listar os eventos: {error}')
        return []

def create_event(service, event_details):
    """Cria um novo evento no calendário principal."""
    try:
        event = service.events().insert(calendarId='primary', body=event_details).execute()
        print(f"Evento criado com sucesso: {event.get('htmlLink')}")
        return event
    except HttpError as error:
        print(f'Ocorreu um erro ao criar o evento: {error}')
        return None

def update_event(service, event_id, updated_details):
    """Atualiza um evento existente."""
    try:
        # Primeiro, recupera o evento para não sobrescrever outros campos
        event = service.events().get(calendarId='primary', eventId=event_id).execute()
        
        # Atualiza os campos desejados
        event.update(updated_details)
        
        updated_event = service.events().update(
            calendarId='primary', eventId=event_id, body=event
        ).execute()
        
        print(f"Evento atualizado com sucesso: {updated_event.get('htmlLink')}")
        return updated_event
    except HttpError as error:
        print(f'Ocorreu um erro ao atualizar o evento: {error}')
        return None

def delete_event(service, event_id):
    """Deleta um evento."""
    try:
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        print(f"Evento com ID '{event_id}' deletado com sucesso.")
    except HttpError as error:
        print(f'Ocorreu um erro ao deletar o evento: {error}')

def main():
    """Função principal para demonstrar as operações no calendário."""
    service = get_calendar_service()
    
    if not service:
        return

    # --- EXEMPLOS DE USO ---
    # Descomente as funções que deseja testar.
    # Para atualizar ou deletar, você precisará de um ID de evento.
    # Use a função list_upcoming_events() para obter os IDs.

    # 1. Listar eventos para obter IDs
    print("\n--- Listando Eventos ---")
    upcoming_events = list_upcoming_events(service)
    
    # 2. Criar um novo evento
    print("\n--- Criando um Evento ---")
    # Definição do evento a ser criado
    new_event_details = {
        'summary': 'Reunião de Planejamento',
        'location': 'Online - Google Meet',
        'description': 'Discutir os próximos passos do projeto.',
        'start': {
            'dateTime': '2025-08-28T14:00:00-03:00',
            'timeZone': 'America/Sao_Paulo',
        },
        'end': {
            'dateTime': '2025-08-28T15:00:00-03:00',
            'timeZone': 'America/Sao_Paulo',
        },
        'attendees': [
            {'email': 'elias.silva882@gmail.com'},
            {'email': 'wandrell1@hotmail.com'},
        ],
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'popup', 'minutes': 30},
            ],
        },
    }
    # Descomente a linha abaixo para criar o evento
    #created_event = create_event(service, new_event_details)

    # 3. Atualizar um evento
    print("\n--- Atualizando um Evento ---")
    if upcoming_events:
        # Exemplo: atualiza o primeiro evento da lista
        event_to_update_id = upcoming_events[0]['id'] 
        update_details = {
            'summary': 'Reunião de Planejamento (NOME ATUALIZADO)',
            'location': 'Escritório Principal, Sala 5',
        }
        # Descomente a linha abaixo para atualizar o evento
        # update_event(service, event_to_update_id, update_details)
    else:
        print("Nenhum evento para atualizar. Crie um primeiro.")

    # 4. Deletar um evento
    print("\n--- Deletando um Evento ---")
    # CUIDADO: Esta ação é permanente!
    # Certifique-se de usar o ID correto.
    if upcoming_events and len(upcoming_events) > 1:
        # Exemplo: deleta o segundo evento da lista
        event_to_delete_id = upcoming_events[1]['id']
        # Descomente a linha abaixo para deletar o evento
        # delete_event(service, event_to_delete_id)
    else:
        print("Não há eventos suficientes na lista para o exemplo de deleção.")


if __name__ == '__main__':
    main()
