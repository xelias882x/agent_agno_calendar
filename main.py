# criando um MCP SERVERS ON line com fastMCP
from fastmcp import FastMCP

# intale as dependencias das ferramentas ex: yfinance , ou google api etc
import yfinance as yf

mcp = FastMCP('yfinance MCP Server')

# tool para buscar o preço de uma açao
# ticker= nome da empresa em str -> retorna um float na saida
@mcp.tool
def get_current_stock_price(ticker: str) -> float:
    '''
    Retorna um valor atual de uma ação com base no
    código da empresa.
    '''
    data = yf.Ticker(ticker)
    return data.fast_info.get('lastPrice')


@mcp.tool
def get_history_stock_price(ticker: str, period: str) -> dict:
    '''
    Retorna histórico do valor  de uma ação
    com base no código da empresa e no periodo.
    period : str
          | Valid periods: 1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max
          | Default: 1mo
          | Can combine whith start/end e.g = start + period
    '''
    data = yf.Ticker(ticker)
    return data.history(period= period).to_dict()


# busacar os dados da empresa
@mcp.tool
def get_company_info(ticker: str) -> dict:
    '''
    Retorna dados compeltos da empresa.
    com base no código da empresa.
    '''
    data = yf.Ticker(ticker)
    return data.info



if __name__ == "__main__":
    # inicia o mcp por padrao em mcp.run(stdio)
    # queremos iniciar com streamble http por padrao
    # main.py == nome do arquivo que tem o script mcp servers (tools)
    # no terminal rode o comando ' fastmcp run main.py --transport http --port 8001 '
    mcp.run()