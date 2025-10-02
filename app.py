import streamlit as st
import os
from agno.agent import Agent
from dotenv import load_dotenv
from agno.models.google.gemini import Gemini
from agno.models.openai import OpenAIChat

# Importe as ferramentas
from calendar_tool import GoogleCalendarTool
from sheets_tool import GoogleSheetsTool
from gmail_tool import GoogleGmailTool

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# --- Configuração dos Agentes ---

# Definição de constantes para os caminhos dos tokens
CALENDAR_TOKEN_PATH = "calendar_token.json"
SHEETS_TOKEN_PATH = "sheets_token.json"
GMAIL_TOKEN_PATH = "gmail_token.json"

# Instruções compartilhadas para os agentes
COMMON_INSTRUCTIONS = [
    "Você é um assistente especializado em gerenciar o Google Calendar, Google Sheets e Gmail.",
    "Sempre responda em Português.",
    "Para qualquer pergunta sobre agenda, compromissos ou eventos, você DEVE usar a ferramenta `GoogleCalendarTool`.",
    "Para qualquer pergunta sobre planilhas, dados ou tabelas, você DEVE usar a ferramenta `GoogleSheetsTool`.",
    "Para qualquer pergunta sobre emails, como ler, procurar ou enviar, você DEVE usar a ferramenta `GoogleGmailTool`.",
    "Não invente informações e não diga que você não tem acesso. Use as ferramentas fornecidas para obter a resposta."
]

# Ferramentas compartilhadas
COMMON_TOOLS = [
    GoogleCalendarTool(token_path=CALENDAR_TOKEN_PATH),
    GoogleSheetsTool(token_path=SHEETS_TOKEN_PATH),
    GoogleGmailTool(token_path=GMAIL_TOKEN_PATH),
]

@st.cache_resource
def get_agents():
    """Cria e armazena em cache as instâncias dos agentes."""
    agents = {
        "Gemini 1.5 Flash": Agent(
            model=Gemini(id="gemini-1.5-flash-latest", api_key=os.getenv("GEMINI_API_KEY")),
            tools=COMMON_TOOLS,
            instructions=COMMON_INSTRUCTIONS,
        ),
        "GPT-4o-mini (OpenAI)": Agent(
            model=OpenAIChat(id="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY")),
            tools=COMMON_TOOLS,
            instructions=COMMON_INSTRUCTIONS,
        ),
        "Modelo Local (Ollama)": Agent(
            model=OpenAIChat(id="gpt-oss:20b", base_url="http://localhost:11434/v1", api_key="ollama"),
            tools=COMMON_TOOLS,
            instructions=COMMON_INSTRUCTIONS,
        ),
    }
    return agents

# --- Interface Streamlit ---

st.set_page_config(page_title="Assistente Google Workspace", layout="wide")
st.title("🤖 Assistente Pessoal para Google Workspace")
st.write("Faça perguntas em linguagem natural para gerenciar seu Calendário, Planilhas e Gmail.")

agents = get_agents()

agent_choice = st.selectbox("Escolha o modelo de IA:", options=list(agents.keys()))

selected_agent = agents[agent_choice]

if prompt := st.chat_input("Digite sua pergunta..."):
    st.chat_message("user").write(prompt)
    with st.chat_message("assistant"):
        # O método run(stream=True) retorna um gerador de eventos.
        # Precisamos extrair o atributo 'content' de cada evento 'RunResponseContent'.
        full_stream = selected_agent.run(prompt, stream=True)
        # Criamos um novo gerador que extrai apenas o texto para o Streamlit.
        text_stream = (event.content for event in full_stream if event.event == "RunResponseContent")
        st.write_stream(text_stream)

# --- Funcionalidade de Reautenticação ---
st.sidebar.header("Configurações Avançadas")
if st.sidebar.button("Limpar Autenticação e Reautenticar"):
    
    def delete_token_files():
        """Deleta os arquivos de token para forçar uma nova autenticação."""
        token_paths = [CALENDAR_TOKEN_PATH, SHEETS_TOKEN_PATH, GMAIL_TOKEN_PATH]
        deleted_files = []
        for token_file in token_paths:
            if os.path.exists(token_file):
                try:
                    os.remove(token_file)
                    deleted_files.append(token_file)
                except OSError as e:
                    st.sidebar.error(f"Erro ao deletar {token_file}: {e}")
        return deleted_files

    deleted = delete_token_files()
    if deleted:
        st.sidebar.success(f"Tokens removidos: {', '.join(deleted)}. A próxima ação irá solicitar nova autenticação.")
        st.cache_resource.clear() # Limpa o cache para recarregar os agentes
    else:
        st.sidebar.info("Nenhum arquivo de token encontrado para remover.")
    st.rerun()