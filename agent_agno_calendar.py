from agno.agent import Agent
from agno.models.openai import OpenAIChat

# Importe a ferramenta do Google Calendar
from calendar_tool import GoogleCalendarTool
# Importe a nova ferramenta do Google Sheets
from sheets_tool import GoogleSheetsTool
# Importe a nova ferramenta personalizada do Gmail
from gmail_tool import GoogleGmailTool

# criando o modelo a ser usado local
agent = Agent(
    model=OpenAIChat(id="gpt-oss:20b", base_url='http://localhost:11434/v1', api_key='ollama'),
    # Agora o agente tem acesso ao Calendário, Sheets e Gmail.
    tools=[
        GoogleCalendarTool(token_path="calendar_token.json"),
        GoogleSheetsTool(token_path="sheets_token.json"),
        GoogleGmailTool(token_path="gmail_token.json"),
    ],
    instructions=[
        "Você é um assistente especializado em gerenciar o Google Calendar, Google Sheets e Gmail.",
        "Sempre responda em Português.",
        "Para qualquer pergunta sobre agenda, compromissos ou eventos, você DEVE usar a ferramenta `GoogleCalendarTool`.",
        "Para qualquer pergunta sobre planilhas, dados ou tabelas, você DEVE usar a ferramenta `GoogleSheetsTool`.",
        "Para qualquer pergunta sobre emails, como ler, procurar ou enviar, você DEVE usar a ferramenta `GoogleGmailTool`.",
        "A ferramenta `list_events` busca os próximos eventos. Use-a quando o usuário perguntar sobre seus compromissos.",
        "A ferramenta `get_spreadsheet_data` busca dados de uma planilha. Use-a quando o usuário pedir para ler uma planilha.",
        "A ferramenta `search_emails` busca por emails. Use-a quando o usuário pedir para procurar por um email.",
        "A ferramenta `get_email_details` busca os detalhes de um email específico. Use-a quando o usuário pedir para ler um email.",
        "A ferramenta `send_email` envia um email. Use-a quando o usuário pedir para enviar um email.",
        "Não invente informações e não diga que você não tem acesso. Use as ferramentas fornecidas para obter a resposta."
    ],
    show_tool_calls=True,
    markdown=True,
)

if __name__ == "__main__":
    # Loop para interagir com o agente no terminal
    while True:
        pergunta = input("Digite sua pergunta (ou 'sair' para encerrar): ")
        if pergunta.lower() == "sair":
            break

        print("Fazendo uma pergunta ao agente...")
        try:
            agent.print_response(pergunta, stream=True)
        except Exception as e:
            print(f"Ocorreu um erro: {e}")


    # Se você quiser usar o playground do Agno, descomente as linhas abaixo:
    # pg = Playground(agents=[agent])
    # app = pg.get_app(use_async=False)
    # pg.serve("agent_agno_calendar:app", reload=True, port=8000)