"""Cria o estilo de impressão DV_PlotStyle.ctb a partir do iX_PlotStyle.ctb.

Porquê (batches de 05-10-2026): nos alçados com "Linhas escondidas = All", o iMos põe as
linhas de fundo no layer IMOS_SECTION_BACK_HIDDEN, que tem a cor 254. O iX_PlotStyle.ctb passa
as cores 8, 9 e 250-253 a preto, mas imprime a 254 com o seu cinzento quase branco
(220,220,220): no PDF as linhas escondidas quase não se viam. E tudo sai com a espessura
mínima, por isso a frente dos móveis não se distingue do que está atrás das portas.

Pedido do Paulo (3.ª volta): "o PDF igual ao que se vê no model". O DV_PlotStyle.ctb é igual
ao iX_PlotStyle.ctb, exceto:
- cor 7 (o que está à vista: layer IMOS_SECTION_BACK, e também as cotas pretas e textos SHX):
  preto a 0,25 mm;
- cor 254 (o que está atrás das portas): cinzento (140,140,140), linha contínua, fina.
  (1.ª volta: cinzento 96 com o tracejado do layer, carregado; 2.ª: pontilhado 110, quase
  invisível.)

Formato do .ctb: 48 bytes de cabeçalho de texto, 3 inteiros (adler32 do bloco comprimido,
tamanho descomprimido, tamanho comprimido) e o texto comprimido com zlib. A espessura é o
índice da custom_lineweight_table (0 = 0,00 mm, 8 = 0,25 mm); o tipo de linha: 31 = o do
objeto, 0 = contínua, 1 = tracejada, 2 = pontilhada.

Uso:
    python scripts/imos_drawing_views/criar_ctb_dv.py <saida.ctb>
O ficheiro fica onde se disser; para o iX CAD o usar tem de ir para I:\\Plotters\\Plot Styles
(o iX_PlotStyle.ctb não é tocado).
"""
from __future__ import annotations

import re
import struct
import sys
import zlib
from pathlib import Path

ORIGEM = Path(r"I:\Plotters\Plot Styles\iX_PlotStyle.ctb")

# cor ACI -> mudanças (rgb None = fica a cor que o iX_PlotStyle já tem)
MUDANCAS = {
    7: {"rgb": None, "linetype": 31, "lineweight": 8},
    254: {"rgb": (140, 140, 140), "linetype": 0, "lineweight": 0},
}


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


def _entrada(texto: str, aci: int) -> re.Match:
    # a tabela começa no 0 para a cor 1
    m = re.search(rf"\n {aci - 1}\{{\n.*?\n \}}\n", texto, re.S)
    if not m:
        raise SystemExit(f"Não encontrei a cor {aci} no .ctb")
    return m


def converter(texto: str) -> str:
    for aci, mud in MUDANCAS.items():
        m = _entrada(texto, aci)
        nova = m.group(0)
        campos = {"linetype": mud["linetype"], "adaptive_linetype": "TRUE",
                  "lineweight": mud["lineweight"]}
        if mud["rgb"] is not None:
            campos["color"] = campos["mode_color"] = cor_ctb(mud["rgb"])
        for chave, valor in campos.items():
            nova = re.sub(rf"\n  {chave}=[^\n]*", f"\n  {chave}={valor}", nova, count=1)
        texto = texto[:m.start()] + nova + texto[m.end():]
    return texto.replace('description="', 'description="DV: frente a 0,25 e fundo (254) cinzento fino', 1)


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    destino = Path(sys.argv[1])
    if destino.exists():
        sys.exit(f"Já existe: {destino} (nada é gravado por cima)")
    gravar(converter(ler(ORIGEM)), destino)
    # confirmação: volta a ler e mostra as entradas mudadas
    t = ler(destino)
    for aci in MUDANCAS:
        print(_entrada(t, aci).group(0).strip())
    print(f"Criado: {destino}")


if __name__ == "__main__":
    main()
