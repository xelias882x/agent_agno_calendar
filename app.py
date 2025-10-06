import streamlit as st
import os
from dotenv import load_dotenv
from llama_index.core import Settings

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.language_models import LLM
from langchain_core.prompts import ChatPromptTemplate

# Importe os componentes
from google_auth import GoogleAuthManager
from calendar_tool import GoogleCalendarTool
from sheets_tool import GoogleSheetsTool
from gmail_tool import GoogleGmailTool
from llama_index.embeddings.gemini import GeminiEmbedding
from rag_setup import get_rag_query_engine
from rag_tool import RAGTool

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# --- Configuração Unificada das Ferramentas e Agentes ---
GOOGLE_TOKEN_PATH = "google_token.json"

# Instruções atualizadas para o agente, agora um assistente de suporte
# O prompt agora é gerenciado pelo LangChain
SYSTEM_PROMPT = """Você é um assistente de suporte e produtividade. Sua principal função é ajudar os usuários fornecendo informações precisas de documentos internos e executando tarefas no Google Workspace.

Regras importantes:
- Sempre responda em Português.
- Para perguntas sobre políticas internas, procedimentos, documentação de projetos ou informações da empresa, você DEVE usar a ferramenta `search_internal_knowledge_base`.
- Você pode e deve combinar ferramentas. Por exemplo: use `search_internal_knowledge_base` para encontrar uma informação e depois use a ferramenta de `send_email`.
- Para qualquer pergunta sobre agenda, compromissos ou eventos, use as ferramentas do Google Calendar.
- Para qualquer pergunta sobre planilhas, dados ou tabelas, use as ferramentas do Google Sheets.
- Para qualquer pergunta sobre e-mails, como ler, procurar ou enviar, use as ferramentas do Gmail.
- Ao usar a ferramenta `search_emails`, construa a 'query' usando o formato de busca do Gmail (ex: 'subject:palavra-chave', 'from:email@exemplo.com', 'is:unread').
- Não invente informações e não diga que você não tem acesso. Use as ferramentas fornecidas para obter a resposta."""

@st.cache_resource
def get_agents():
    """Cria e armazena em cache as instâncias dos agentes e ferramentas."""
    # 1. Define todos os escopos necessários para as ferramentas
    all_scopes = list(set(GoogleCalendarTool.SCOPES + GoogleSheetsTool.SCOPES + GoogleGmailTool.SCOPES))

    # 2. Cria o gerenciador de autenticação e as ferramentas base do Google
    auth_manager = GoogleAuthManager(scopes=all_scopes, token_path=GOOGLE_TOKEN_PATH)
    calendar = GoogleCalendarTool(auth_manager)
    sheets = GoogleSheetsTool(auth_manager)
    gmail = GoogleGmailTool(auth_manager)
    
    google_tools = calendar.get_tools() + sheets.get_tools() + gmail.get_tools()

    # 3. Define os modelos de LLM
    gemini_llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", temperature=0, google_api_key=os.getenv("GEMINI_API_KEY"))
    # IMPORTANTE: Verifique o nome exato do seu modelo local executando `ollama list` no terminal
    # e substitua o valor de `model` abaixo pelo nome correto.
    local_llm = ChatOpenAI(model="gpt-oss:20b", base_url="http://localhost:11434/v1", api_key="ollama", temperature=0)

    # 4. Cria o prompt do agente
    prompt_template = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ]
    )

    # 5. Função para criar um agente
    def create_agent(llm: LLM):
        # A configuração global do LlamaIndex é feita dentro de get_rag_query_engine
        # para garantir que seja executada antes da criação do motor de busca.
        rag_tool = RAGTool(
            query_engine=get_rag_query_engine(llm=llm, embed_model=GeminiEmbedding(model_name="models/text-embedding-004", api_key=os.getenv("GEMINI_API_KEY")))
        )
        all_tools = google_tools + [rag_tool]
        agent = create_tool_calling_agent(llm, all_tools, prompt_template)
        return AgentExecutor(agent=agent, tools=all_tools, verbose=True)

    # 6. Cria os agentes
    agents = {
        "Gemini 1.5 Flash": create_agent(gemini_llm),
        "Modelo Local (Ollama)": create_agent(local_llm),
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
    st.session_state.messages = {}

# Inicializa o histórico para o agente selecionado, se não existir
if agent_choice not in st.session_state.messages:
    st.session_state.messages[agent_choice] = []

# Exibe as mensagens do histórico
for message in st.session_state.messages[agent_choice]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Digite sua pergunta..."):
    # Adiciona e exibe a mensagem do usuário
    st.session_state.messages[agent_choice].append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    # Obtém o agente selecionado
    selected_agent = agents[agent_choice]

    # Gera e exibe a resposta do assistente
    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            # Constrói o histórico para o LangChain
            chat_history = []
            for msg in st.session_state.messages[agent_choice][:-1]: # Pega todo o histórico exceto a última pergunta
                if msg["role"] == "user":
                    chat_history.append(("human", msg["content"]))
                elif msg["role"] == "assistant":
                    chat_history.append(("ai", msg["content"]))

            # Usa .stream() para respostas em tempo real e st.write_stream para exibir
            stream = selected_agent.stream({"input": prompt, "chat_history": chat_history})
            # O 'output' vem dentro de um dicionário, então extraímos o valor de cada chunk
            full_response = st.write_stream(chunk["output"] for chunk in stream if "output" in chunk)
            st.session_state.messages[agent_choice].append({"role": "assistant", "content": full_response})

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
    if agent_choice in st.session_state.messages:
        st.session_state.messages[agent_choice] = []
    st.rerun()