import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.language_models import LLM
from langchain_core.prompts import ChatPromptTemplate
from llama_index.embeddings.gemini import GeminiEmbedding as GoogleGenerativeAIEmbedding

from google_auth import GoogleAuthManager
from calendar_tool import GoogleCalendarTool
from sheets_tool import GoogleSheetsTool
from gmail_tool import GoogleGmailTool
from rag_setup import get_rag_query_engine
from rag_tool import RAGTool


GOOGLE_TOKEN_PATH = "google_token.json"

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

def get_google_tools(scopes):
    """Cria e gerencia as ferramentas do Google Workspace."""
    auth_manager = GoogleAuthManager(token_path=GOOGLE_TOKEN_PATH, scopes=scopes)
    calendar_tool = GoogleCalendarTool(auth_manager=auth_manager)
    sheets_tool = GoogleSheetsTool(auth_manager=auth_manager)
    gmail_tool = GoogleGmailTool(auth_manager=auth_manager)
    return (
        calendar_tool.get_tools()
        + sheets_tool.get_tools()
        + gmail_tool.get_tools()
    )

def create_agent_executor(llm: LLM, tools: list, prompt: ChatPromptTemplate) -> AgentExecutor:
    """Cria um AgentExecutor com o LLM, ferramentas e prompt fornecidos."""
    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)

def get_all_agents():
    """Cria e retorna um dicionário com todas as instâncias de agentes configurados."""
    all_scopes = list(set(GoogleCalendarTool.SCOPES + GoogleSheetsTool.SCOPES + GoogleGmailTool.SCOPES))
    google_tools = get_google_tools(scopes=all_scopes)

    gemini_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-latest", temperature=0, google_api_key=os.getenv("GEMINI_API_KEY"))
    local_llm = ChatOpenAI(model="gpt-oss:20b", base_url="http://localhost:11434/v1", api_key="ollama", temperature=0)

    prompt_template = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ]
    )

    embed_model = GoogleGenerativeAIEmbedding(model_name="models/text-embedding-004", api_key=os.getenv("GEMINI_API_KEY"))
    
    rag_tool_gemini = RAGTool(query_engine=get_rag_query_engine(llm=gemini_llm, embed_model=embed_model))
    rag_tool_local = RAGTool(query_engine=get_rag_query_engine(llm=local_llm, embed_model=embed_model))

    agents = {
        "Gemini 1.5 Flash": create_agent_executor(gemini_llm, google_tools + [rag_tool_gemini.as_tool()], prompt_template),
        "Modelo Local (Ollama)": create_agent_executor(local_llm, google_tools + [rag_tool_local.as_tool()], prompt_template),
    }
    return agents