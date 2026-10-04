"""Ferramentas das ferragens do iMos (``scripts/imos_ferragens``).

A parte que fala com a consola do iX CAD não se testa aqui (precisa do iX CAD
instalado); testa-se o que vem a seguir: ler o SAT, ler os cortes em DXF R12,
refazer o volume pela regra par/ímpar e desenhar. E guarda-se a regra de os
.ps1 serem só ASCII — o PowerShell 5.1 lê os .ps1 sem BOM como ANSI e estraga
os acentos.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from scripts.imos_ferragens import dxf_leitura, sat, volume

PASTA = Path(__file__).resolve().parents[1] / "scripts" / "imos_ferragens"


# ------------------------------------------------------------------------ SAT
def test_tokens_cadeia_com_espacos_e_cardinal():
    fichas = sat.tokens("DXID-attrib $-1 @9 a # b c d $3 #")
    assert ("S", "a # b c d") in fichas
    assert fichas[-1] == ("T", "#")


def test_registos_e_referencias(tmp_path):
    texto = (
        "700 0 1 0\n@7 produto\n1 9.9e-07 1e-10\n"
        "body $-1 -1 $-1 $1 $-1 $-1 #\n"
        "lump $-1 -1 $-1 $-1 $-1 $0 #\n"
    )
    caminho = tmp_path / "peca.sat"
    caminho.write_text(texto, encoding="latin-1")
    regs = sat.registos(caminho)
    assert [r[0] for r in regs] == ["body", "lump"]
    assert sat.ref(regs[0][4]) == 1
    assert sat.ref(regs[1][6]) == 0
    assert sat.ref("2.5") is None


# ------------------------------------------------------------------------ DXF
def test_bulge_positivo_e_meia_volta_no_sentido_direto():
    pts = dxf_leitura.pontos_bulge((0, 0), (2, 0), 1.0)
    raios = np.linalg.norm(pts - [1, 0], axis=1)
    assert np.allclose(raios, 1.0)
    assert np.allclose(pts[0], [0, 0]) and np.allclose(pts[-1], [2, 0])
    meio = pts[len(pts) // 2]
    assert meio[1] == pytest.approx(-1.0, abs=0.01)


def _dxf_r12(entidades_blocos: dict[str, list[str]], inserts: list[str]) -> str:
    linhas = ["0", "SECTION", "2", "BLOCKS"]
    for nome, corpo in entidades_blocos.items():
        linhas += ["0", "BLOCK", "8", "0", "2", nome, "70", "1",
                   "10", "0.0", "20", "0.0", "30", "0.0", "3", nome, "1", ""]
        linhas += corpo
        linhas += ["0", "ENDBLK", "8", "0"]
    linhas += ["0", "ENDSEC", "0", "SECTION", "2", "ENTITIES"]
    for nome in inserts:
        linhas += ["0", "INSERT", "8", "0", "2", nome, "10", "0.0", "20", "0.0", "30", "0.0"]
    linhas += ["0", "ENDSEC", "0", "EOF"]
    return "\n".join(linhas) + "\n"


def _linha(p, q):
    return ["0", "LINE", "8", "CORTES",
            "10", str(p[0]), "20", str(p[1]), "30", str(p[2]),
            "11", str(q[0]), "21", str(q[1]), "31", str(q[2])]


def _quadrado(x0, y0, x1, y1, z):
    c = [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]
    return sum((_linha(c[i], c[(i + 1) % 4]) for i in range(4)), [])


def test_ler_regioes_so_blocos_usados_e_circulo_com_normal_ao_contrario(tmp_path):
    circulo = ["0", "CIRCLE", "8", "CORTES", "10", "2.0", "20", "3.0", "30", "-0.5",
               "40", "1.0", "210", "0.0", "220", "0.0", "230", "-1.0"]
    texto = _dxf_r12(
        {"*U1": _quadrado(0, 0, 10, 10, 0.0), "*U2": circulo, "*U9": _quadrado(0, 0, 1, 1, 9.0)},
        ["*U1", "*U2"],
    )
    caminho = tmp_path / "cortes.dxf"
    caminho.write_text(texto, encoding="latin-1")
    regioes = dxf_leitura.ler_regioes(caminho)
    assert len(regioes) == 2  # o *U9 não é usado
    assert len(regioes[0]) == 4
    P = np.vstack(regioes[1])
    # normal (0,0,-1): o X do objeto é o -X do mundo e a elevação -0.5 fica +0.5
    assert np.allclose(P[:, 2], 0.5)
    assert np.allclose(np.linalg.norm(P[:, :2] - [-2.0, 3.0], axis=1), 1.0)


# --------------------------------------------------------------------- volume
def _regiao(*quadrados):
    """Região com vários contornos (quadrados em z=0)."""
    fora = []
    for x0, y0, x1, y1 in quadrados:
        c = np.array([(x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0), (x0, y0, 0)], float)
        fora.append(c)
    return fora


def test_furo_dentro_da_regiao_fica_vazio():
    cortes = volume.voxelizar([_regiao((0, 0, 10, 10), (3, 3, 7, 7))], 0.5, 0.0, 0.5)
    assert cortes.V.sum() == 20 * 20 - 8 * 8


def test_regioes_sobrepostas_juntam_se_em_vez_de_se_anularem():
    cortes = volume.voxelizar([_regiao((0, 0, 4, 4)), _regiao((2, 0, 6, 4))], 0.5, 0.0, 0.5)
    assert cortes.V.sum() == 12 * 8  # 6 x 4 mm em voxels de 0,5


def test_contorno_aberto_nao_risca_ate_a_borda():
    aberto = [np.array([(0, 0, 0), (0, 10, 0)], float)]
    cortes = volume.voxelizar([aberto, _regiao((20, 0, 22, 2))], 0.5, 0.0, 0.5)
    assert cortes.V.sum() == 4 * 4


def test_corte_que_falhou_no_meio_fica_igual_ao_de_baixo():
    def em_z(z):
        return [np.array([(0, 0, z), (4, 0, z), (4, 4, z), (0, 4, z), (0, 0, z)], float)]

    # cortes a 0, 0.5, (1.0 falhou), 1.5
    cortes = volume.voxelizar([em_z(0.0), em_z(0.5), em_z(1.5)], 0.5, 0.0, 0.5)
    areas = cortes.V.sum(axis=(1, 2))
    assert list(areas[:4]) == [64, 64, 64, 64]
    assert areas[4:].sum() == 0  # para lá do último corte não se inventa nada


def test_carregar_cortes_le_o_json_do_cortes_ps1(tmp_path):
    corpo = _quadrado(0, 0, 4, 4, 1.0)
    caminho = tmp_path / "c.dxf"
    caminho.write_text(_dxf_r12({"*U1": corpo, "*U2": _quadrado(0, 0, 4, 4, 1.5)}, ["*U1", "*U2"]),
                       encoding="latin-1")
    (tmp_path / "c.dxf.json").write_text(json.dumps({"de": 1.0, "passo": 0.5, "cortes": 2}))
    cortes = volume.carregar_cortes(caminho)
    assert cortes.V.shape[0] >= 2
    assert cortes.V[0].sum() == cortes.V[1].sum() == 8 * 8
    assert cortes.origem[2] == pytest.approx(1.0)


def test_carregar_cortes_sem_json_pede_os_numeros(tmp_path):
    caminho = tmp_path / "c.dxf"
    caminho.write_text(_dxf_r12({"*U1": _quadrado(0, 0, 1, 1, 0.0)}, ["*U1"]), encoding="latin-1")
    with pytest.raises(ValueError):
        volume.carregar_cortes(caminho)


def test_render_caixa_da_imagem_quadrada_com_fundo_branco():
    V = np.zeros((40, 30, 20), bool)
    V[5:35, 5:25, 5:15] = True
    cortes = volume.Cortes(V=V, origem=np.zeros(3), passo=0.5)
    im = volume.render(cortes, (-0.5, -1, -0.45), tamanho=64, supersample=2, sigma=1.0)
    arr = np.asarray(im)
    assert im.size == (64, 64)
    assert tuple(arr[0, 0]) == (255, 255, 255)  # canto = fundo
    assert (arr.sum(axis=2) < 3 * 250).sum() > 200  # a peça aparece


def test_render_luz_vem_de_cima():
    """Cubo visto a 45° por cima: a face de cima (metade de cima da imagem) tem de
    sair mais clara que a da frente — a luz é dada em relação à câmara."""
    V = np.zeros((40, 40, 40), bool)
    V[5:35, 5:35, 5:35] = True
    cortes = volume.Cortes(V=V, origem=np.zeros(3), passo=0.5)
    im = np.asarray(volume.render(cortes, (0, 1, -1), tamanho=96, supersample=2, sigma=1.0,
                                  sombra=False)).astype(float).sum(axis=2)
    cima = im[20:30, 40:56].mean()   # parte de cima da imagem = face de cima
    frente = im[66:76, 40:56].mean()  # parte de baixo = face da frente
    assert cima > frente


# -------------------------------------------------------------------- scripts
@pytest.mark.parametrize("ps1", sorted(PASTA.rglob("*.ps1")), ids=lambda p: p.name)
def test_ps1_so_ascii(ps1):
    dados = ps1.read_bytes()
    fora = [i for i, b in enumerate(dados) if b > 127]
    assert not fora, f"{ps1.name} tem caracteres não ASCII (o PowerShell 5.1 estraga-os)"


def test_readme_cita_todos_os_comandos():
    readme = (PASTA / "README.md").read_text(encoding="utf-8")
    for nome in ("step_para_dwg.ps1", "arestas.ps1", "cortes.ps1", "instalar_na_biblioteca.ps1",
                 "imos_ferragens.sat", "imos_ferragens.arame", "imos_ferragens.vistas",
                 "imos_ferragens.imagem", "imos_ferragens.sobrepor", "imos_ferragens.ficha_pdf",
                 "exemplos/nivelador_levelup.ps1"):
        assert nome in readme, nome
