"""Coleta de livros do books.toscrape.com (site feito pra treinar scraping)."""

import time
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://books.toscrape.com/"

# o site usa a nota em inglês na classe CSS (star-rating Three)
ESTRELAS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PortfolioScraper/1.0)"}


def criar_sessao(tentativas: int = 3) -> requests.Session:
    """Sessão que tenta de novo em erro 429/5xx, esperando 0.5s, 1s, 2s..."""
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


_sessao: Optional[requests.Session] = None


def _obter_sessao() -> requests.Session:
    global _sessao
    if _sessao is None:
        _sessao = criar_sessao()
    return _sessao


@dataclass
class Livro:
    titulo: str
    preco: float
    avaliacao: int  # 1 a 5
    disponivel: bool
    categoria: str
    url: str


def obter_pagina(url: str) -> Optional[BeautifulSoup]:
    """Baixa a página e devolve o HTML parseado, ou None se der erro."""
    try:
        resposta = _obter_sessao().get(url, timeout=10)
        resposta.raise_for_status()
        resposta.encoding = "utf-8"  # sem isso o £ vem quebrado
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
    livros = []

    for artigo in soup.find_all("article", class_="product_pod"):
        try:
            # o texto do link vem cortado, o título completo fica no atributo title
            titulo = artigo.h3.a["title"]
            url = urljoin(url_pagina, artigo.h3.a["href"])

            preco_texto = artigo.find("p", class_="price_color").text
            preco = float(re.sub(r"[^\d.]", "", preco_texto))

            classes = artigo.find("p", class_="star-rating")["class"]
            palavra = next((c for c in classes if c in ESTRELAS), None)
            avaliacao = ESTRELAS.get(palavra, 0)

            disponivel = "In stock" in artigo.find("p", class_="instock").text

            livros.append(Livro(titulo, preco, avaliacao, disponivel, categoria, url))
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            print(f"  Aviso: não foi possível extrair um livro ({e})")

    return livros


def raspar_categoria(url_categoria: str, nome_categoria: str,
                     max_paginas: int = 5, delay: float = 1.0) -> list[Livro]:
    """Percorre as páginas da categoria seguindo o botão "next"."""
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
        print(f"    {len(livros_pagina)} livros nesta página")

        proximo = soup.find("li", class_="next")
        if proximo and proximo.a and pagina < max_paginas:
            url_atual = urljoin(url_atual, proximo.a["href"])
            pagina += 1
            time.sleep(delay)  # pra não sobrecarregar o site
        else:
            break

    print(f"  Total coletado: {len(todos_livros)} livros")
    return todos_livros


def obter_categorias(max_categorias: int = 5, nomes: Optional[list[str]] = None) -> list[tuple[str, str]]:
    soup = obter_pagina(BASE_URL)
    if soup is None:
        return []
    return extrair_categorias(soup, max_categorias, nomes)


def extrair_categorias(soup: BeautifulSoup, max_categorias: int = 5,
                       nomes: Optional[list[str]] = None) -> list[tuple[str, str]]:
    """Lê o menu lateral e devolve [(nome, url), ...].

    Com `nomes`, devolve só essas categorias (sem diferenciar maiúscula), na ordem pedida.
    Sem `nomes`, devolve as `max_categorias` primeiras.
    """
    nav = soup.find("ul", class_="nav-list")
    if not nav:
        return []

    # o primeiro link é "Books", que tem tudo
    todas = [(link.text.strip(), urljoin(BASE_URL, link["href"])) for link in nav.find_all("a")[1:]]
    if not nomes:
        return todas[:max_categorias]

    por_nome = {nome.lower(): (nome, url) for nome, url in todas}
    return [por_nome[n.strip().lower()] for n in nomes if n.strip().lower() in por_nome]
