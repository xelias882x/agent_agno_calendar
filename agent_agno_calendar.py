from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.playground import Playground , serve_playground_app

# Importe a nova ferramenta do Google Calendar
from calendar_tool import GoogleCalendarTool

# criando o modelo a ser usado local
agent = Agent(
    model=OpenAIChat(id="gpt-oss:20b",base_url='http://localhost:11434/v1', api_key='ollama'),
    # Para simplificar o teste, vamos fornecer apenas a ferramenta de calendário.
    # Isso aumenta a chance do modelo escolher a ferramenta correta.
    tools=[
        GoogleCalendarTool(),
    ],
    instructions=[ # Instruções mais diretas para forçar o uso da ferramenta
        "Você é um assistente especializado em gerenciar o Google Calendar.",
        "Sempre responda em Português.",
        "Para qualquer pergunta sobre agenda, compromissos ou eventos, você DEVE usar a ferramenta `GoogleCalendarTool`.",
        "A ferramenta `list_events` busca os próximos eventos. Use-a quando o usuário perguntar sobre seus compromissos.",
        "Não invente informações e não diga que você não tem acesso. Use as ferramentas fornecidas para obter a resposta."
    ],
    show_tool_calls=True,
    markdown=True,
)

# acessando o dashboard do agno
app = Playground(agents=[agent]).get_app()

if __name__ == "__main__":
    # A linha abaixo inicia o servidor web para o Playground do Agno.
    # O servidor irá recarregar automaticamente quando você salvar o arquivo.
    print("Iniciando o servidor local para o Playground do Agno...")
    print("Aguarde a URL do Playground que será exibida abaixo para acessar a interface.")
    # Para iniciar o dashboard web, descomente a linha abaixo.
    # serve_playground_app("agent_agno_calendar:app", reload=True, port=8000)

    # Se você quiser apenas fazer uma pergunta ao agente pela linha de comando,
    # comente a linha do servidor acima e descomente a linha abaixo.
    print("Fazendo uma pergunta ao agente...")
    agent.print_response("Crie um evento para 'testando as novas tools da api calendar' para o dia 29/08/2025 inicio as 11:00 horas termino as 12:00 horas", stream=True)