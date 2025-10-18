# Assistente Pessoal para Google Workspace 🤖

Este projeto é um assistente pessoal inteligente, construído em Python, que integra e orquestra diversas APIs do Google Workspace. O núcleo do sistema é um agente de IA que interpreta comandos em linguagem natural para interagir com os serviços do Google, facilitando a automação de tarefas de produtividade.

A interface é construída com Streamlit, permitindo uma interação amigável e conversacional diretamente no navegador.

## ✨ Funcionalidades Principais

-   **🗓️ Google Calendar:**
    -   Listar os próximos eventos.
    -   Criar novos eventos.
    -   Atualizar eventos existentes (inclusive alterando apenas a hora).
    -   Excluir eventos.
-   **📊 Google Sheets:**
    -   Ler dados de planilhas e exibi-los em formato de tabela.
    -   Atualizar células.
    -   Adicionar novas linhas de dados.
-   **📧 Gmail:**
    -   Pesquisar e-mails com filtros avançados.
    -   Ler detalhes e resumos de e-mails.
    -   Enviar e-mails.
-   **🧠 Base de Conhecimento (RAG):** Pesquisar e responder perguntas com base em documentos internos (`.txt`, `.md`, `.pdf`, `.xlsx`, `.csv`). O agente pode combinar informações internas com outras ferramentas (ex: encontrar uma política e enviá-la por e-mail).

## 🚀 Tecnologias Utilizadas

-   **Linguagem:** Python 3.9+
-   **Interface Web:** Streamlit
-   **Framework de Agente:** `agno`
-   **Framework de Agente:** `LangChain`
-   **Modelos de IA Suportados:**
    -   Google Gemini (ex: `gemini-1.5-flash-latest`)
    -   Modelos locais via Ollama (ex: `gtp-oss:20b`, `llama3`)
-   **APIs:** Google Calendar, Google Sheets, Google Gmail
-   **RAG (Retrieval-Augmented Generation):**
    -   `llama-index` para orquestração.
    -   `chromadb` como banco de dados vetorial persistente.

## ⚙️ Configuração do Ambiente

Siga os passos abaixo para configurar e executar o projeto em sua máquina local.

### 1. Pré-requisitos

-   Python 3.9 ou superior.
-   Acesso a uma conta Google.

### 2. Configuração da API do Google

Para que o assistente possa acessar seus dados, você precisa configurar as credenciais na Google Cloud Platform.

1.  Acesse o Google Cloud Console.
2.  Crie um novo projeto.
3.  No menu de navegação, vá para **APIs e Serviços > Biblioteca** e ative as seguintes APIs:
    -   `Google Calendar API`
    -   `Google Sheets API`
    -   `Gmail API`
4.  Vá para **APIs e Serviços > Tela de permissão OAuth**.
    -   Selecione tipo de usuário **Externo** e crie a tela.
    -   Preencha as informações necessárias (nome do app, e-mail de suporte).
    -   Na tela de Escopos, não adicione nada.
    -   Adicione seu próprio e-mail como **Usuário de teste**.
5.  Vá para **APIs e Serviços > Credenciais**.
    -   Clique em **Criar Credenciais > ID do cliente OAuth**.
    -   Selecione o tipo de aplicativo **App para computador**.
    -   Após a criação, anote o **ID do Cliente** e a **Chave Secreta do Cliente**.

### 3. Instalação das Dependências

Clone o repositório, crie um ambiente virtual e instale os pacotes necessários.

```bash
# Crie e ative um ambiente virtual
python -m venv env
# No Windows:
.\env\Scripts\activate
# No macOS/Linux:
# source env/bin/activate

# Instale as bibliotecas a partir do arquivo requirements.txt
pip install -r requirements.txt
```

### 4. Variáveis de Ambiente

Crie um arquivo chamado `.env` na raiz do projeto e adicione as credenciais obtidas.

```ini
# Chaves para os modelos de IA (adicione as que for usar)
GEMINI_API_KEY="SUA_CHAVE_API_DO_GEMINI"

# Credenciais do Google Cloud OAuth
GOOGLE_CLIENT_ID="SEU_ID_DE_CLIENTE_OAUTH.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET="SUA_CHAVE_SECRETA_DO_CLIENTE"
GOOGLE_PROJECT_ID="ID_DO_SEU_PROJETO_NO_GOOGLE_CLOUD"
```

## ▶️ Como Executar

1.  Certifique-se de que seu ambiente virtual está ativado.
2.  Execute o seguinte comando no terminal:

    ```bash
    streamlit run app.py
    ```

3.  Seu navegador abrirá com a interface do assistente.
4.  Na primeira vez que você fizer uma pergunta que precise de uma ferramenta do Google, uma aba do navegador se abrirá para você fazer login e autorizar o acesso do aplicativo à sua conta.

## 💬 Como Usar

-   Selecione o modelo de IA que deseja usar no menu suspenso.
-   Digite suas perguntas em linguagem natural no campo de chat.
-   Use os botões na barra lateral para limpar o histórico da conversa ou para reautenticar (caso as permissões expirem).

**Exemplos de perguntas:**
-   "Quais são meus próximos 5 compromissos?"
-   "Marque uma reunião com o time de vendas amanhã às 15h com o título 'Alinhamento Semanal'."
-   "Encontre os últimos e-mails com 'relatório' no assunto."
-   "Envie um e-mail para `exemplo@email.com` com o assunto 'Feedback' e corpo 'Olá, tudo bem?'"

---

*Este projeto demonstra a integração poderosa entre modelos de linguagem e APIs de produtividade para criar assistentes inteligentes e personalizados.*