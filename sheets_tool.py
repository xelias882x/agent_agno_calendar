from typing import Any, List, Optional

from agno.tools import Toolkit
from agno.utils.log import log_error, log_info

try:
    from googleapiclient.errors import HttpError

except ImportError:
    raise ImportError(
        "Google client libraries not found, Please install using `pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib`"
    )

from google_auth import GoogleAuthManager


class GoogleSheetsTool(Toolkit):
    """Um toolkit para interagir com a API do Google Sheets."""

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

    def __init__(
        self,
        auth_manager: GoogleAuthManager,
        **kwargs,
    ):
        self.auth_manager = auth_manager
        super().__init__(
            name="GoogleSheetsTool",
            tools=[
                self.get_spreadsheet_data,
                self.update_spreadsheet_data,
                self.append_spreadsheet_data,
            ],
            **kwargs,
        )
        log_info("Ferramenta Google Sheets conectada com sucesso.")

    @property
    def service(self):
        return self.auth_manager.get_service("sheets", "v4")

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
            result = self.service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute() # type: ignore
            values = result.get("values", [])
            if not values:
                return "Nenhum dado encontrado na planilha."
            
            # Formata a saída como uma tabela Markdown
            header = values[0]
            # Garante que todas as linhas tenham o mesmo número de colunas que o cabeçalho
            num_columns = len(header)
            table = [f"| {' | '.join(map(str, header))} |"]
            table.append(f"|{'-|' * num_columns}")
            
            for row in values[1:]:
                # Preenche as células vazias para alinhar a tabela
                padded_row = row + [''] * (num_columns - len(row))
                table.append(f"| {' | '.join(map(str, padded_row[:num_columns]))} |")
            
            return "\n".join(table)
        except HttpError as error:
            return f"Ocorreu um erro ao ler a planilha: {error}"

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
            result = self.service.spreadsheets().values().update( # type: ignore
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="USER_ENTERED",
                body=body,
            ).execute()
            updated_cells = result.get('updatedCells', 0)
            return f"{updated_cells} células foram atualizadas com sucesso na planilha."
        except HttpError as error:
            return f"Ocorreu um erro ao atualizar a planilha: {error}"

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
            self.service.spreadsheets().values().append( # type: ignore
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body=body,
            ).execute()
            return f"Dados adicionados com sucesso na planilha '{spreadsheet_id}'."
        except HttpError as error:
            return f"Ocorreu um erro ao adicionar dados na planilha: {error}"