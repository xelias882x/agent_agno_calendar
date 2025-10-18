import base64
import logging
from email.mime.text import MIMEText
from typing import Any, Dict
from typing import List, Optional

from langchain_core.tools import tool, StructuredTool

try:
    from googleapiclient.errors import HttpError

except ImportError:
    raise ImportError(
        "Google client libraries not found, Please install using `pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib`"
    )

from google_auth import GoogleAuthManager


class GoogleGmailTool:
    """Um toolkit para interagir com a API do Gmail."""

    SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
    ]

    def __init__(self, auth_manager: GoogleAuthManager):
        self.auth_manager = auth_manager
        logging.info("Ferramenta Google Gmail conectada com sucesso.")

    def get_tools(self) -> List[Any]:
        """Retorna uma lista de todas as ferramentas disponíveis neste toolkit."""
        return [
            StructuredTool.from_function(self.search_emails),
            StructuredTool.from_function(self.get_email_details),
            StructuredTool.from_function(self.send_email),
        ]

    def service(self):
        """Método auxiliar para obter o serviço autenticado da API."""
        return self.auth_manager.get_service("gmail", "v1")

    def search_emails(self, query: str, max_results: int = 5) -> str:
        """
        Busca e-mails na caixa de entrada do usuário que correspondam a uma consulta específica.
        A consulta deve seguir o formato de pesquisa do Gmail.

        Exemplos de consulta:
        - Para buscar e-mails com "MCP" no assunto: 'subject:MCP'
        - Para buscar e-mails de 'exemplo@email.com': 'from:exemplo@email.com'
        - Para buscar e-mails não lidos: 'is:unread'
        """
        try:
            logging.info(f"Buscando e-mails com a consulta: '{query}'")
            result = self.service().users().messages().list(userId="me", q=query, maxResults=max_results).execute()  # type: ignore
            messages = result.get("messages", [])
            if not messages:
                return "Nenhum e-mail encontrado com o critério especificado."

            email_summaries = []
            for msg in messages:
                msg_details = self.service().users().messages().get(userId="me", id=msg['id'], format='metadata', metadataHeaders=['Subject', 'From', 'Date']).execute() # type: ignore
                headers = msg_details.get('payload', {}).get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Sem assunto')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Remetente desconhecido')
                email_summaries.append(f"- De: {sender}, Assunto: {subject} (ID: {msg['id']})")
            
            return "E-mails encontrados:\n" + "\n".join(email_summaries)

        except HttpError as error:
            return f"Ocorreu um erro ao buscar e-mails: {error}"

    def get_email_details(self, message_id: str) -> str:
        """Gets the full details of a specific email message."""
        try:
            message = self.service().users().messages().get(userId="me", id=message_id).execute() # type: ignore
            payload = message.get('payload', {})
            headers = payload.get('headers', [])
            
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Sem assunto')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Remetente desconhecido')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Data desconhecida')
            
            snippet = message.get('snippet', 'Nenhum conteúdo prévio disponível.')

            return (
                f"Detalhes do E-mail (ID: {message_id}):\n"
                f"De: {sender}\n"
                f"Assunto: {subject}\n"
                f"Data: {date}\n"
                f"--- Trecho ---\n{snippet}"
            )

        except HttpError as error:
            return f"Ocorreu um erro ao obter detalhes do e-mail: {error}"

    def send_email(self, to: str, subject: str, body: str) -> str:
        """Sends an email from the authenticated user's account."""
        try:
            message = MIMEText(body)
            message["to"] = to
            message["subject"] = subject
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            create_message = {"raw": raw_message}
            self.service().users().messages().send(userId="me", body=create_message).execute() # type: ignore
            return f"E-mail enviado com sucesso para '{to}' com o assunto '{subject}'."
        except HttpError as error:
            return f"Ocorreu um erro ao enviar o e-mail: {error}"