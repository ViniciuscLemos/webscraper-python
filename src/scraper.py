"""
Módulo de Scraping — Web Scraper
==================================
Coleta dados do site books.toscrape.com, que é um site feito especialmente
para praticar web scraping (não causa danos a nenhum sistema real).

Conceitos que você vai aprender:
- HTTP requests com a biblioteca requests
- Sessões HTTP e novas tentativas automáticas (retry com backoff)
- Parsing de HTML com BeautifulSoup
- Navegação pela estrutura do DOM (tags, classes CSS)
- Paginação: como percorrer múltiplas páginas automaticamente
- Rate limiting: esperar entre requisições para não sobrecarregar o servidor
- Dataclasses: forma moderna de definir classes de dados em Python
"""

import time
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# URL base do site alvo (site feito para praticar scraping)
BASE_URL = "https://books.toscrape.com/"

# Mapeamento de estrelas (o site usa palavras em inglês)
ESTRELAS = {
    "One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5
}

# Headers para identificar o scraper
# Sites podem bloquear requisições sem User-Agent
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PortfolioScraper/1.0)"
}


def criar_sessao(tentativas: int = 3) -> requests.Session:
    """
    Cria uma sessão HTTP que reaproveita conexões e tenta de novo em falhas
    temporárias (erros 429/5xx ou queda de conexão), esperando cada vez mais
    entre as tentativas (0.5s, 1s, 2s...) — isso se chama backoff exponencial.
    """
    sessao = requests.Session()
    sessao.headers.update(HEADERS)
    retry = Retry(
        total=tentativas,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    sessao.mount("http://", HTTPAdapter(max_retries=retry))
    sessao.mount("https://", HTTPAdapter(max_retries=retry))
    return sessao


# Sessão compartilhada pelo módulo (criada na primeira requisição)
_sessao: Optional[requests.Session] = None


def _obter_sessao() -> requests.Session:
    global _sessao
    if _sessao is None:
        _sessao = criar_sessao()
    return _sessao


@dataclass
class Livro:
    """
    Dataclass: forma pythônica de criar classes de dados.
    O decorador @dataclass gera __init__, __repr__ e __eq__ automaticamente.
    """
    titulo: str
    preco: float
    avaliacao: int  # 1 a 5 estrelas
    disponivel: bool
    categoria: str
    url: str


def obter_pagina(url: str) -> Optional[BeautifulSoup]:
    """
    Faz uma requisição HTTP GET e retorna o HTML parseado.

    Retorna None em caso de erro (sem lançar exceção).
    Isso permite que o chamador decida o que fazer com a falha.
    """
    try:
        # timeout=10: não espera mais de 10 segundos por resposta
        resposta = _obter_sessao().get(url, timeout=10)

        # raise_for_status() lança exceção se o status for 4xx ou 5xx
        resposta.raise_for_status()

        # O site declara UTF-8; sem isso o símbolo £ pode vir corrompido
        resposta.encoding = "utf-8"

        # BeautifulSoup parseia o HTML — "html.parser" é o nativo do Python
        return BeautifulSoup(resposta.text, "html.parser")

    except requests.exceptions.ConnectionError:
        print(f"  Erro de conexão ao acessar: {url}")
    except requests.exceptions.Timeout:
        print(f"  Timeout ao acessar: {url}")
    except requests.exceptions.HTTPError as e:
        print(f"  Erro HTTP {e.response.status_code}: {url}")
    except requests.exceptions.RequestException as e:
        print(f"  Falha na requisição ({e.__class__.__name__}): {url}")
    return None


def extrair_livros_da_pagina(soup: BeautifulSoup, categoria: str, url_pagina: str) -> list[Livro]:
    """
    Extrai os dados de todos os livros de uma página de listagem.

    Inspecione o HTML do site para entender a estrutura:
    - Cada livro está em um <article class="product_pod">
    - O título está no atributo 'title' do <a> dentro do <h3>
    - O preço está no <p class="price_color">
    - As estrelas estão na classe CSS do <p class="star-rating CLASSE">

    url_pagina é usada para transformar links relativos ("../../livro/index.html")
    em absolutos com urljoin.
    """
    livros = []

    # find_all() retorna uma lista de todas as tags que correspondem ao critério
    artigos = soup.find_all("article", class_="product_pod")

    for artigo in artigos:
        try:
            # Título: está no atributo 'title' (o texto visível é truncado)
            titulo = artigo.h3.a["title"]

            # urljoin resolve "../" do jeito que o navegador faria
            url = urljoin(url_pagina, artigo.h3.a["href"])

            # Preço: remove o símbolo £ e converte para float
            preco_texto = artigo.find("p", class_="price_color").text
            preco = float(re.sub(r"[^\d.]", "", preco_texto))

            # Avaliação: a classe CSS contém a quantidade de estrelas
            # Ex: <p class="star-rating Three"> → 3 estrelas
            classe_estrelas = artigo.find("p", class_="star-rating")["class"]
            palavra_estrela = next((c for c in classe_estrelas if c in ESTRELAS), None)
            avaliacao = ESTRELAS.get(palavra_estrela, 0)

            # Disponibilidade
            disponivel = "In stock" in artigo.find("p", class_="instock").text

            livros.append(Livro(
                titulo=titulo,
                preco=preco,
                avaliacao=avaliacao,
                disponivel=disponivel,
                categoria=categoria,
                url=url
            ))

        except (AttributeError, KeyError, TypeError, ValueError) as e:
            # Ignora livros com estrutura inesperada e continua
            print(f"  Aviso: não foi possível extrair um livro ({e})")
            continue

    return livros


def raspar_categoria(url_categoria: str, nome_categoria: str,
                     max_paginas: int = 5, delay: float = 1.0) -> list[Livro]:
    """
    Percorre todas as páginas de uma categoria e coleta os livros.

    Parâmetros:
        url_categoria  — URL da primeira página da categoria
        nome_categoria — nome para categorizar os livros coletados
        max_paginas    — limite de páginas (evita loops infinitos)
        delay          — segundos de espera entre requisições (rate limiting)
    """
    todos_livros = []
    url_atual = url_categoria
    pagina = 1

    print(f"\nColetando categoria: {nome_categoria}")

    while url_atual and pagina <= max_paginas:
        print(f"  Página {pagina}: {url_atual}")

        soup = obter_pagina(url_atual)
        if soup is None:
            break

        livros_pagina = extrair_livros_da_pagina(soup, nome_categoria, url_atual)
        todos_livros.extend(livros_pagina)
        print(f"    {len(livros_pagina)} livros coletados nesta página")

        # Verifica se existe uma próxima página
        # O botão "next" tem um <li class="next"> com um <a href="...">
        proximo = soup.find("li", class_="next")
        if proximo and proximo.a and pagina < max_paginas:
            url_atual = urljoin(url_atual, proximo.a["href"])
            pagina += 1

            # Rate limiting: espera entre requisições (boa prática)
            time.sleep(delay)
        else:
            break  # Última página (ou limite atingido)

    print(f"  Total coletado: {len(todos_livros)} livros")
    return todos_livros


def obter_categorias(max_categorias: int = 5) -> list[tuple[str, str]]:
    """
    Obtém a lista de categorias disponíveis no site.
    Retorna lista de tuplas: [(nome, url), ...]
    """
    soup = obter_pagina(BASE_URL)
    if soup is None:
        return []
    return extrair_categorias(soup, max_categorias)


def extrair_categorias(soup: BeautifulSoup, max_categorias: int = 5) -> list[tuple[str, str]]:
    """Lê as categorias do menu lateral: <ul class="nav nav-list">."""
    nav = soup.find("ul", class_="nav-list")
    if not nav:
        return []

    categorias = []
    for link in nav.find_all("a")[1:max_categorias + 1]:  # Pula "Books" (índice 0)
        nome = link.text.strip()
        url = urljoin(BASE_URL, link["href"])
        categorias.append((nome, url))

    return categorias
