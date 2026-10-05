"""
Testes do scraper que não acessam a internet: usam HTML de exemplo
com a mesma estrutura do books.toscrape.com.
"""

import csv
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest import mock

from bs4 import BeautifulSoup

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src import scraper  # noqa: E402
from src.exportar import exportar_csv, exportar_json, imprimir_relatorio, remover_duplicados  # noqa: E402
from src.scraper import Livro  # noqa: E402


def artigo(titulo, href, preco, estrelas, estoque="In stock"):
    return f"""
    <article class="product_pod">
      <p class="star-rating {estrelas}"></p>
      <h3><a href="{href}" title="{titulo}">{titulo[:10]}...</a></h3>
      <div class="product_price">
        <p class="price_color">£{preco}</p>
        <p class="instock availability">{estoque}</p>
      </div>
    </article>"""


def pagina(artigos, proxima=None):
    nav = f'<li class="next"><a href="{proxima}">next</a></li>' if proxima else ""
    return BeautifulSoup(f"<html><body>{''.join(artigos)}<ul class='pager'>{nav}</ul></body></html>",
                         "html.parser")


URL_CATEGORIA = "https://books.toscrape.com/catalogue/category/books/travel_2/index.html"


class TestExtracao(unittest.TestCase):
    def test_extrai_campos(self):
        soup = pagina([artigo("A Light in the Attic", "../../../a-light-in-the-attic_1000/index.html",
                              "51.77", "Three")])
        livros = scraper.extrair_livros_da_pagina(soup, "Poetry", URL_CATEGORIA)
        self.assertEqual(len(livros), 1)
        livro = livros[0]
        self.assertEqual(livro.titulo, "A Light in the Attic")
        self.assertEqual(livro.preco, 51.77)
        self.assertEqual(livro.avaliacao, 3)
        self.assertTrue(livro.disponivel)
        self.assertEqual(livro.categoria, "Poetry")
        # urljoin resolve os "../" a partir da página atual
        self.assertEqual(livro.url, "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html")

    def test_fora_de_estoque_e_estrela_desconhecida(self):
        soup = pagina([artigo("X", "x/index.html", "10.00", "Zero", estoque="Out of stock")])
        livro = scraper.extrair_livros_da_pagina(soup, "C", URL_CATEGORIA)[0]
        self.assertFalse(livro.disponivel)
        self.assertEqual(livro.avaliacao, 0)

    def test_ignora_livro_malformado(self):
        quebrado = '<article class="product_pod"><h3></h3></article>'
        soup = pagina([quebrado, artigo("Ok", "ok/index.html", "1.00", "One")])
        with redirect_stdout(StringIO()):
            livros = scraper.extrair_livros_da_pagina(soup, "C", URL_CATEGORIA)
        self.assertEqual([l.titulo for l in livros], ["Ok"])

    def test_extrai_categorias(self):
        soup = BeautifulSoup("""
            <ul class="nav nav-list"><li><a href="catalogue/category/books_1/index.html">Books</a>
              <ul>
                <li><a href="catalogue/category/books/travel_2/index.html"> Travel </a></li>
                <li><a href="catalogue/category/books/mystery_3/index.html"> Mystery </a></li>
              </ul></li></ul>""", "html.parser")
        categorias = scraper.extrair_categorias(soup, max_categorias=5)
        self.assertEqual(categorias, [
            ("Travel", "https://books.toscrape.com/catalogue/category/books/travel_2/index.html"),
            ("Mystery", "https://books.toscrape.com/catalogue/category/books/mystery_3/index.html"),
        ])


class TestPaginacao(unittest.TestCase):
    def setUp(self):
        self.paginas = {
            URL_CATEGORIA: pagina([artigo("A", "a/index.html", "1.00", "One")], proxima="page-2.html"),
            URL_CATEGORIA.replace("index.html", "page-2.html"):
                pagina([artigo("B", "b/index.html", "2.00", "Two")], proxima="page-3.html"),
            URL_CATEGORIA.replace("index.html", "page-3.html"):
                pagina([artigo("C", "c/index.html", "3.00", "Five")]),
        }

    def raspar(self, max_paginas):
        with mock.patch.object(scraper, "obter_pagina", side_effect=self.paginas.get), \
             mock.patch.object(scraper.time, "sleep") as dormir, \
             redirect_stdout(StringIO()):
            livros = scraper.raspar_categoria(URL_CATEGORIA, "Travel", max_paginas=max_paginas, delay=1)
        return livros, dormir

    def test_segue_todas_as_paginas(self):
        livros, dormir = self.raspar(max_paginas=10)
        self.assertEqual([l.titulo for l in livros], ["A", "B", "C"])
        self.assertEqual(dormir.call_count, 2)  # espera entre as páginas, não depois da última

    def test_respeita_limite_de_paginas(self):
        livros, dormir = self.raspar(max_paginas=2)
        self.assertEqual([l.titulo for l in livros], ["A", "B"])
        self.assertEqual(dormir.call_count, 1)

    def test_para_quando_a_pagina_falha(self):
        with mock.patch.object(scraper, "obter_pagina", return_value=None), redirect_stdout(StringIO()):
            self.assertEqual(scraper.raspar_categoria(URL_CATEGORIA, "Travel"), [])


class TestExportacao(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.livros = [
            Livro("A", 10.0, 5, True, "Travel", "https://x/a"),
            Livro("B", 20.0, 3, False, "Poetry", "https://x/b"),
            Livro("A de novo", 10.0, 5, True, "Travel", "https://x/a"),
        ]

    def tearDown(self):
        self.pasta.cleanup()

    def test_remove_duplicados_por_url(self):
        self.assertEqual([l.titulo for l in remover_duplicados(self.livros)], ["A", "B"])

    def test_csv(self):
        caminho = os.path.join(self.pasta.name, "sub", "livros.csv")
        exportar_csv(self.livros[:2], caminho)
        with open(caminho, encoding="utf-8") as f:
            linhas = list(csv.DictReader(f))
        self.assertEqual(linhas[1]["titulo"], "B")
        self.assertEqual(linhas[1]["disponivel"], "False")

    def test_json(self):
        caminho = os.path.join(self.pasta.name, "livros.json")
        exportar_json(self.livros[:2], caminho)
        with open(caminho, encoding="utf-8") as f:
            self.assertEqual(json.load(f)[0]["preco"], 10.0)

    def test_relatorio(self):
        saida = StringIO()
        with redirect_stdout(saida):
            imprimir_relatorio(self.livros[:2])
            imprimir_relatorio([])
        texto = saida.getvalue()
        self.assertIn("Total de livros: 2", texto)
        self.assertIn("Preço médio:     £15.00", texto)
        self.assertIn("Nenhum livro coletado", texto)


if __name__ == "__main__":
    unittest.main()
