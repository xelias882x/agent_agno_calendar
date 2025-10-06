import os
import chromadb
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, Settings
from llama_index.core.base.llms.base import BaseLLM
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.response_synthesizers import get_response_synthesizer
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.chroma import ChromaVectorStore

# --- Constantes ---
KNOWLEDGE_BASE_DIR = "./knowledge_base"
DB_PATH = "./chroma_db"
COLLECTION_NAME = "internal_docs"

def get_rag_query_engine(llm: BaseLLM, embed_model: BaseEmbedding):
    """
    Configura e retorna um motor de busca RAG (query engine).
    Cria um índice vetorial a partir de documentos locais se ele não existir,
    ou carrega o índice existente para reutilização.
    :param llm: O modelo de linguagem a ser usado para a síntese da resposta.
    :param embed_model: O modelo de embedding a ser usado para vetorizar os documentos.
    """
    # Configura o LLM e o modelo de embedding globalmente para o LlamaIndex
    Settings.llm = llm
    Settings.embed_model = embed_model

    # Garante que o diretório da base de conhecimento exista
    if not os.path.exists(KNOWLEDGE_BASE_DIR):
        os.makedirs(KNOWLEDGE_BASE_DIR)

    # Inicializa o cliente ChromaDB, que armazena os vetores
    db = chromadb.PersistentClient(path=DB_PATH)
    chroma_collection = db.get_or_create_collection(COLLECTION_NAME)

    # Configura o contexto de armazenamento para usar o ChromaDB
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # --- Otimização da Indexação ---
    # Configura um "parser" mais inteligente para dividir os documentos em pedaços (chunks)
    # que respeitam as sentenças, melhorando a qualidade da busca.
    node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=20)

    # Carrega documentos de múltiplos formatos (.txt, .md, .pdf, .xlsx) da pasta.
    # Para que .xlsx funcione, a biblioteca 'pandas' e 'openpyxl' devem estar instaladas.
    # O LlamaIndex é eficiente: ele verifica o hash dos arquivos e só reprocessa
    # aqueles que são novos ou foram modificados desde a última indexação.
    documents = []
    if os.listdir(KNOWLEDGE_BASE_DIR):
        # Inicializa o leitor e carrega os documentos apenas se a pasta não estiver vazia.
        reader = SimpleDirectoryReader(
            input_dir=KNOWLEDGE_BASE_DIR,
            required_exts=[".txt", ".md", ".pdf", ".xlsx", ".csv"]
        )
        documents = reader.load_data()

    # Cria o índice a partir dos documentos carregados.
    index = VectorStoreIndex.from_documents(
        documents, storage_context=storage_context, transformations=[node_parser]
    )

    # --- Otimização da Resposta do RAG ---
    # Configura um "sintetizador de resposta" personalizado.
    # Se os documentos encontrados não forem relevantes para a pergunta,
    # o LLM é instruído a retornar uma resposta padrão, evitando alucinações.
    response_synthesizer = get_response_synthesizer(
        response_mode="compact",
        text_qa_template="""Com base no contexto fornecido, responda à pergunta. Se o contexto não contiver a resposta, diga 'Não encontrei uma resposta para sua pergunta na base de conhecimento.'.\n\nContexto:\n{context_str}\n\nPergunta: {query_str}\n\nResposta:""",
    )

    # Retorna o motor de busca pronto para ser usado
    return index.as_query_engine(response_synthesizer=response_synthesizer)