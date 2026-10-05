"""Cria o estilo de impressão DV_PlotStyle.ctb a partir do iX_PlotStyle.ctb.

Porquê (batch de 05-10-2026): nos alçados com "Linhas escondidas = All", o iMos põe as
linhas de fundo no layer IMOS_SECTION_BACK_HIDDEN, que tem a cor 254. O iX_PlotStyle.ctb passa
as cores 8, 9 e 250-253 a preto, mas imprime a 254 com o seu cinzento quase branco
(220,220,220): no PDF as linhas escondidas quase não se viam.

O DV_PlotStyle.ctb é igual ao iX_PlotStyle.ctb, exceto a cor 254, que passa a cinzento
médio (110,110,110) e pontilhado fino, sem engrossar. Assim as linhas escondidas continuam a
distinguir-se das linhas à vista (preto contínuo), mas veem-se.

Formato do .ctb: 48 bytes de cabeçalho de texto, 3 inteiros (adler32 do bloco comprimido,
tamanho descomprimido, tamanho comprimido) e o texto comprimido com zlib.

Uso:
    python scripts/imos_drawing_views/criar_ctb_dv.py <saida.ctb>
O ficheiro fica onde se disser; para o iX CAD o usar tem de ir para I:\\Plotters\\Plot Styles
(ficheiro NOVO: o iX_PlotStyle.ctb não é tocado).
"""
from __future__ import annotations

import re
import struct
import sys
import zlib
from pathlib import Path

ORIGEM = Path(r"I:\Plotters\Plot Styles\iX_PlotStyle.ctb")
CINZENTO = (110, 110, 110)
# tipo de linha do .ctb: 31 = o do objeto, 0 = contínua, 1 = tracejada, 2 = pontilhada.
# 2.ª versão (05-10, tarde): com o tracejado do layer o PDF ficava carregado; pontilhado fino
# lê-se como o ecrã do iX CAD.
TIPO_LINHA = 2


def cor_ctb(rgb: tuple[int, int, int]) -> int:
    """0xC3RRGGBB como inteiro com sinal (é assim que o .ctb guarda as cores fixas)."""
    v = 0xC3000000 | (rgb[0] << 16) | (rgb[1] << 8) | rgb[2]
    return v - (1 << 32)


def ler(ctb: Path) -> str:
    b = ctb.read_bytes()
    return zlib.decompress(b[60:]).decode("latin-1")


def gravar(texto: str, destino: Path) -> None:
    dados = texto.encode("latin-1")
    comp = zlib.compress(dados)
    cab = ORIGEM.read_bytes()[:48]
    destino.write_bytes(cab + struct.pack("<III", zlib.adler32(comp), len(dados), len(comp)) + comp)


def converter(texto: str) -> str:
    cor = cor_ctb(CINZENTO)
    entrada = re.search(r"\n 253\{\n.*?\n \}\n", texto, re.S)
    if not entrada:
        raise SystemExit("Não encontrei a cor 254 no .ctb")
    nova = entrada.group(0)
    for chave, valor in (("color", cor), ("mode_color", cor), ("linetype", TIPO_LINHA),
                         ("adaptive_linetype", "TRUE"), ("lineweight", 0)):
        nova = re.sub(rf"\n  {chave}=[^\n]*", f"\n  {chave}={valor}", nova, count=1)
    texto = texto[:entrada.start()] + nova + texto[entrada.end():]
    return texto.replace('description="', 'description="DV: iX_PlotStyle com a cor 254 escura', 1)


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    destino = Path(sys.argv[1])
    if destino.exists():
        sys.exit(f"Já existe: {destino} (nada é gravado por cima)")
    gravar(converter(ler(ORIGEM)), destino)
    # confirmação: volta a ler e mostra a cor 254
    print(re.search(r"\n 253\{\n.*?\n \}", ler(destino), re.S).group(0))
    print(f"Criado: {destino}")


if __name__ == "__main__":
    main()
