import streamlit as st
import os
from agno.agent import Agent
from dotenv import load_dotenv
from agno.models.google.gemini import Gemini
from agno.models.openai import OpenAIChat

# Importe as ferramentas
from google_auth import GoogleAuthManager
from calendar_tool import GoogleCalendarTool
from sheets_tool import GoogleSheetsTool
from gmail_tool import GoogleGmailTool

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# --- Configuração Unificada das Ferramentas e Agentes ---
GOOGLE_TOKEN_PATH = "google_token.json"

# Instruções compartilhadas para os agentes
COMMON_INSTRUCTIONS = [
    "Você é um assistente especializado em gerenciar o Google Calendar, Google Sheets e Gmail.",
    "Sempre responda em Português.",
    "Para qualquer pergunta sobre agenda, compromissos ou eventos, você DEVE usar a ferramenta `GoogleCalendarTool`.",
    "Para qualquer pergunta sobre planilhas, dados ou tabelas, você DEVE usar a ferramenta `GoogleSheetsTool`.",
    "Para qualquer pergunta sobre e-mails, como ler, procurar ou enviar, você DEVE usar a ferramenta `GoogleGmailTool`.",
    "Ao usar a ferramenta `search_emails`, construa a 'query' usando o formato de busca do Gmail (ex: 'subject:palavra-chave', 'from:email@exemplo.com', 'is:unread').",
    "Não invente informações e não diga que você não tem acesso. Use as ferramentas fornecidas para obter a resposta."
]

@st.cache_resource
def get_agents():
    """Cria e armazena em cache as instâncias dos agentes e ferramentas."""
    # 1. Define todos os escopos necessários para as ferramentas
    all_scopes = list(set(GoogleCalendarTool.SCOPES + GoogleSheetsTool.SCOPES + GoogleGmailTool.SCOPES))

    # 2. Cria uma única instância do gerenciador de autenticação
    auth_manager = GoogleAuthManager(scopes=all_scopes, token_path=GOOGLE_TOKEN_PATH)

    # 3. Injeta o gerenciador de autenticação em cada ferramenta
    common_tools = [
        GoogleCalendarTool(auth_manager=auth_manager),
        GoogleSheetsTool(auth_manager=auth_manager),
        GoogleGmailTool(auth_manager=auth_manager),
    ]

    # 4. Cria os agentes com as ferramentas unificadas
    agents = {
        "Gemini 1.5 Flash": Agent(
            model=Gemini(id="gemini-1.5-flash-latest", api_key=os.getenv("GEMINI_API_KEY")),
            tools=common_tools,
            instructions=COMMON_INSTRUCTIONS,
        ),
        "GPT-4o-mini (OpenAI)": Agent(
            model=OpenAIChat(id="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY")), # type: ignore
            tools=common_tools,
            instructions=COMMON_INSTRUCTIONS,
        ),
        "Modelo Local (Ollama)": Agent(
            model=OpenAIChat(id="gpt-oss:20b", base_url="http://localhost:11434/v1", api_key="ollama"), # type: ignore
            tools=common_tools,
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

# --- Gerenciamento do Histórico de Conversa ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Exibe as mensagens do histórico
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Digite sua pergunta..."):
    # Adiciona e exibe a mensagem do usuário
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    # Obtém o agente selecionado
    selected_agent = agents[agent_choice]

    # Gera e exibe a resposta do assistente
    with st.chat_message("assistant"):
        # Passa o histórico para o agente (se a biblioteca suportar)
        # A biblioteca 'agno' gerencia a sessão internamente através da instância do agente,
        # que já está em cache. Apenas enviar o novo prompt é suficiente para manter o contexto.
        with st.spinner("Pensando..."):
            full_stream = selected_agent.run(prompt, stream=True)
            text_stream = (event.content for event in full_stream if event.event == "RunResponseContent")
            
            # st.write_stream retorna a string completa, que salvamos no histórico
            full_response = st.write_stream(text_stream)
            st.session_state.messages.append({"role": "assistant", "content": full_response})

# --- Funcionalidade de Reautenticação ---
st.sidebar.header("Configurações Avançadas")
if st.sidebar.button("Limpar Autenticação e Reautenticar"):
    
    def delete_token_files():
        """Deleta o arquivo de token unificado para forçar uma nova autenticação."""
        # Agora só precisamos deletar um arquivo
        token_paths = [GOOGLE_TOKEN_PATH]
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
        st.cache_resource.clear() # Limpa o cache para recarregar os agentes e o auth_manager
    else:
        st.sidebar.info("Nenhum arquivo de token encontrado para remover.")
    st.rerun()

if st.sidebar.button("Nova Conversa"):
    st.session_state.messages = []
    # Opcional: Limpar a sessão do agente se a biblioteca 'agno' tiver um método para isso.
    # Por enquanto, apenas limpamos o histórico da interface.
    st.rerun()