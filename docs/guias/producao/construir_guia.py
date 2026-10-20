"""Constrói o guia do menu Produção: um só HTML (imagens lá dentro) e o PDF.

Os prints originais estão em ``capturas/`` (tirados do Martelo a 100 %). Aqui
recortam-se, apagam-se os dados que não interessam (email do cliente) e
gravam-se em ``img/`` como WebP. O ``guia_producao.html`` é a fonte que se
edita: aponta para ``img/``. O ficheiro para distribuir é o
``Guia_Producao_Martelo_V3.html``, com as imagens embutidas, que abre em
qualquer PC sem internet nem pastas ao lado.

Uso (a partir desta pasta):
    python construir_guia.py            # imagens + HTML final
    python construir_guia.py --pdf      # e também o PDF (pelo Microsoft Edge)
    python construir_guia.py --grelha form   # grelha para marcar coordenadas
"""

from __future__ import annotations

import base64
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

PASTA = Path(__file__).resolve().parent
CAPTURAS = PASTA / "capturas"
IMG = PASTA / "img"
FONTE = PASTA / "guia_producao.html"
SAIDA_HTML = PASTA / "Guia_Producao_Martelo_V3.html"
SAIDA_PDF = PASTA / "Guia_Producao_Martelo_V3.pdf"

# nome -> (captura, recorte (x0, y0, x1, y1) ou None, zonas a desfocar)
RECORTES: dict[str, tuple[str, tuple[int, int, int, int] | None, list]] = {
    "ecra": ("01_ecra_producao.png", (0, 30, 2560, 1170), []),
    "capa_imagem": ("01_ecra_producao.png", (1748, 282, 2360, 585), []),
    "botoes": ("01_ecra_producao.png", (224, 130, 1720, 178), []),
    "filtros_esq": ("01_ecra_producao.png", (224, 180, 1590, 218), []),
    "filtros_dir": ("01_ecra_producao.png", (1580, 178, 2540, 220), []),
    "form": ("01_ecra_producao.png", (228, 252, 1588, 632), []),
    "imagem_pasta": ("01_ecra_producao.png", (1580, 278, 2528, 642), []),
    "textos": ("01_ecra_producao.png", (228, 640, 2528, 975), []),
    "tabela": ("01_ecra_producao.png", (228, 985, 2528, 1160), []),
    "campo_imos": ("01_ecra_producao.png", (1120, 296, 1588, 336), []),
    "menu_funcoes": ("02_menu_funcoes.png", (680, 130, 1500, 390), []),
    "menu_cutrite": ("03_menu_cutrite.png", (680, 130, 1300, 250), []),
    "converter": ("04_converter_orcamento.png", None, []),
    "novo_processo": ("05_novo_processo_phc.png", None, []),
    "lista_existe": ("06_lista_material_existe.png", None, []),
    "listas_imos": ("07_gerar_listas_imos.png", None, []),
    "analise_materiais": ("08_analise_materiais.png", (0, 0, 2000, 540), []),
    "analise_custos": ("09_analise_custos.png", (0, 40, 1700, 700), []),
    "preparacao": ("10_preparacao.png", (0, 0, 1400, 815), []),
    "preferencias": ("11_preparacao_preferencias.png", None, []),
    "imprimir": ("12_imprimir.png", (0, 560, 1700, 1350), []),
    "imprimir_btn": ("12_imprimir.png", (2330, 578, 2552, 620), []),
    "pdf_cutrite": ("12_imprimir.png", (1377, 62, 2028, 528), []),
    "exportar_pdf": ("13_exportar_documentacao.png", None, []),
    # O endereço do cliente não vai para um documento que circula.
    "notificar": ("14_notificar_cliente.png", None, [(86, 45, 400, 69)]),
    "criar_imos": ("15_criar_encomenda_imos.png", None, []),
    "ocorrencias_obra": ("16_ocorrencias_obra.png", None, []),
    "novo_ticket": ("17_ocorrencia_novo_ticket.png", None, []),
    "pagina_ocorrencias": ("18_pagina_ocorrencias.png", (212, 92, 2548, 720), []),
    "ocorrencias_rodape": ("18_pagina_ocorrencias.png", (215, 1283, 960, 1375), []),
    "menu_colunas": ("19_menu_colunas.png", (900, 400, 1700, 1040), []),
    "tooltip": ("20_tooltip_cutrite.png", (830, 128, 1420, 198), []),
    "novo_modelo": ("21_novo_modelo_versao.png", None, []),
}


def preparar_imagem(nome: str) -> Image.Image:
    captura, recorte, desfocar = RECORTES[nome]
    imagem = Image.open(CAPTURAS / captura).convert("RGB")
    for zona in desfocar:
        pedaco = imagem.crop(zona).filter(ImageFilter.GaussianBlur(7))
        imagem.paste(pedaco, zona[:2])
    if recorte:
        imagem = imagem.crop(recorte)
    return imagem


def gravar_imagens() -> dict[str, tuple[int, int]]:
    IMG.mkdir(exist_ok=True)
    tamanhos = {}
    for nome in RECORTES:
        imagem = preparar_imagem(nome)
        imagem.save(IMG / f"{nome}.webp", "WEBP", quality=90, method=6)
        tamanhos[nome] = imagem.size
    return tamanhos


def grelha(nome: str, destino: Path) -> None:
    """Grelha de 50 px por cima do recorte, para ler coordenadas dos pinos."""
    imagem = preparar_imagem(nome)
    desenho = ImageDraw.Draw(imagem)
    fonte = ImageFont.load_default()
    largura, altura = imagem.size
    for x in range(0, largura, 50):
        cor = (220, 0, 0) if x % 250 == 0 else (255, 150, 150)
        desenho.line([(x, 0), (x, altura)], fill=cor, width=1)
        if x % 100 == 0:
            desenho.text((x + 2, 2), str(x), fill=(200, 0, 0), font=fonte)
    for y in range(0, altura, 50):
        cor = (0, 0, 220) if y % 250 == 0 else (150, 150, 255)
        desenho.line([(0, y), (largura, y)], fill=cor, width=1)
        if y % 100 == 0:
            desenho.text((2, y + 2), str(y), fill=(0, 0, 200), font=fonte)
    imagem.save(destino)
    print(destino, imagem.size)


def embutir(html: str) -> str:
    def trocar(achado: re.Match) -> str:
        ficheiro = IMG / achado.group(1)
        dados = base64.b64encode(ficheiro.read_bytes()).decode("ascii")
        return f'src="data:image/webp;base64,{dados}"'

    return re.sub(r'src="img/([\w.-]+\.webp)"', trocar, html)


def gerar_pdf() -> None:
    edge = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    if not edge.exists():
        raise SystemExit("Microsoft Edge não encontrado: o PDF não foi gerado.")
    subprocess.run(
        [
            str(edge),
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            "--virtual-time-budget=8000",
            f"--print-to-pdf={SAIDA_PDF}",
            SAIDA_HTML.as_uri() + "?imprimir",
        ],
        check=True,
        timeout=180,
    )
    print(SAIDA_PDF, f"{SAIDA_PDF.stat().st_size / 1e6:.1f} MB")


def main() -> None:
    if "--grelha" in sys.argv:
        nome = sys.argv[sys.argv.index("--grelha") + 1]
        destino = Path(sys.argv[sys.argv.index("--grelha") + 2]) if len(sys.argv) > sys.argv.index("--grelha") + 2 else PASTA / f"_grelha_{nome}.png"
        grelha(nome, destino)
        return
    tamanhos = gravar_imagens()
    for nome, (w, h) in tamanhos.items():
        print(f"{nome:20s} {w}x{h}")
    SAIDA_HTML.write_text(embutir(FONTE.read_text(encoding="utf-8")), encoding="utf-8")
    print(SAIDA_HTML, f"{SAIDA_HTML.stat().st_size / 1e6:.1f} MB")
    if "--pdf" in sys.argv:
        gerar_pdf()


if __name__ == "__main__":
    main()
