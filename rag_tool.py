from langchain_core.tools import BaseTool
from typing import Any

class RAGTool(BaseTool):
    """
    Ferramenta para realizar buscas em uma base de conhecimento interna de documentos.
    """
    name: str = "search_internal_knowledge_base"
    description: str = "Use esta ferramenta para responder perguntas sobre políticas internas, procedimentos, documentação de projetos ou qualquer outra informação que possa estar nos documentos da empresa."
    query_engine: Any

    def _run(self, query: str) -> str:
        try:
            response = self.query_engine.query(query)
            return str(response)
        except Exception as e:
            return f"Ocorreu um erro ao buscar na base de conhecimento: {e}"

    async def _arun(self, query: str) -> str:
        # Langchain pode tentar usar a versão assíncrona, então implementamos por segurança
        return self._run(query)