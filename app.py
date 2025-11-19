import streamlit as st
import os
from dotenv import load_dotenv
from agent_factory import get_all_agents

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

@st.cache_resource
def get_agents():
    """Função de cache para carregar os agentes a partir da factory."""
    return get_all_agents()

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

            try:
                # Usa .stream() para respostas em tempo real e st.write_stream para exibir
                stream = selected_agent.stream({"input": prompt, "chat_history": chat_history})
                # O 'output' vem dentro de um dicionário, então extraímos o valor de cada chunk
                full_response = st.write_stream(chunk["output"] for chunk in stream if "output" in chunk)
                st.session_state.messages[agent_choice].append({"role": "assistant", "content": full_response})
            except Exception as e:
                st.error(f"Ocorreu um erro ao processar sua solicitação: {e}")
                st.session_state.messages[agent_choice].append({"role": "assistant", "content": "Desculpe, não consegui processar sua solicitação. Tente novamente."})

def delete_token_files():
    """Deleta o arquivo de token unificado para forçar uma nova autenticação."""
    # Agora só precisamos deletar um arquivo
    token_paths = ["google_token.json"] # Caminho direto para o token
    deleted_files = []
    for token_file in token_paths:
        if os.path.exists(token_file):
            try:
                os.remove(token_file)
                deleted_files.append(token_file)
            except OSError as e:
                st.sidebar.error(f"Erro ao deletar {token_file}: {e}")
    return deleted_files

# --- Funcionalidade de Reautenticação ---
st.sidebar.header("Configurações Avançadas")
if st.sidebar.button("Limpar Autenticação e Reautenticar"):
    deleted = delete_token_files()
    if deleted:
        st.sidebar.success(f"Tokens removidos: {', '.join(deleted)}. A próxima ação irá solicitar nova autenticação.")
        st.cache_resource.clear() # Limpa o cache para recarregar os agentes e o auth_manager
    else:
        st.sidebar.info("Nenhum arquivo de token encontrado para remover.")
    st.rerun()

if st.sidebar.button("Nova Conversa"):
    # Limpa o histórico de todos os agentes para uma experiência de reset completa
    if "messages" in st.session_state:
        st.session_state.messages = {}
    st.rerun()
    