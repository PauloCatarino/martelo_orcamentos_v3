"""Arrumar as chaves de um modelo ValueSet por grupo, como o navegador mostra."""

from __future__ import annotations

from types import SimpleNamespace

from app.domain.valueset_navegador_chaves import (
    ORDEM_DESCONHECIDA,
    agrupar_linhas,
    agrupar_linhas_contiguas,
    indice_grupo,
    meta_da_chave,
    metas_por_codigo,
    ordenar_linhas_por_grupo_e_chave,
    rotulo_grupo,
)


def _chave(codigo: str, nome: str, grupo: str, ordem: int):
    return SimpleNamespace(codigo=codigo, nome=nome, grupo=grupo, ordem=ordem)


def _linha(id: int, chave: str, prioridade: int | None = 1):
    return SimpleNamespace(id=id, chave=chave, prioridade=prioridade)


VOCABULARIO = [
    _chave("MATERIAL_COSTAS", "Costas", "MATERIAIS", 3),
    _chave("FERRAGEM_VARAO", "Varão", "FERRAGENS", 4),
    _chave("FERRAGEM_SUPORTE_LATERAL_VARAO", "Suporte lateral", "FERRAGENS", 5),
    _chave("ACABAMENTO_FACE_SUP", "Face superior", "ACABAMENTOS", 1),
]

METAS = metas_por_codigo(VOCABULARIO)


def test_os_grupos_saem_pela_ordem_de_quem_orca() -> None:
    linhas = [
        _linha(1, "ACABAMENTO_FACE_SUP"),
        _linha(2, "FERRAGEM_VARAO"),
        _linha(3, "MATERIAL_COSTAS"),
    ]

    grupos = agrupar_linhas(linhas, METAS)

    # Materiais antes de ferragens, ferragens antes de acabamentos — e não por
    # ordem alfabética, que punha os acabamentos em primeiro.
    assert [grupo.codigo for grupo in grupos] == [
        "MATERIAIS",
        "FERRAGENS",
        "ACABAMENTOS",
    ]


def test_dentro_do_grupo_as_chaves_seguem_a_ordem_do_vocabulario() -> None:
    linhas = [
        _linha(1, "FERRAGEM_SUPORTE_LATERAL_VARAO"),
        _linha(2, "FERRAGEM_VARAO"),
    ]

    grupos = agrupar_linhas(linhas, METAS)

    assert [chave.codigo for chave in grupos[0].chaves] == [
        "FERRAGEM_VARAO",
        "FERRAGEM_SUPORTE_LATERAL_VARAO",
    ]


def test_chave_orfa_fica_a_vista_em_sem_grupo() -> None:
    """Uma chave que o vocabulário já não conhece é a que dá problemas.

    No custeio ela deixa o dropdown "Mat. default" vazio, sem erro nenhum. Aqui
    tem de aparecer, e não desaparecer no meio das outras.
    """
    linhas = [_linha(1, "MATERIAL_COSTAS"), _linha(2, "FERRAGEM_SUPORTE_VARAO")]

    grupos = agrupar_linhas(linhas, METAS)

    assert grupos[-1].codigo == ""
    assert grupos[-1].rotulo == "Sem grupo"
    assert [chave.codigo for chave in grupos[-1].chaves] == [
        "FERRAGEM_SUPORTE_VARAO"
    ]


def test_meta_de_chave_desconhecida_usa_o_proprio_codigo() -> None:
    meta = meta_da_chave("FERRAGEM_SUPORTE_VARAO", METAS)

    assert meta.nome == "FERRAGEM_SUPORTE_VARAO"
    assert meta.grupo == ""
    assert meta.ordem == ORDEM_DESCONHECIDA


def test_grupo_novo_nao_cai_no_fim_com_as_orfas() -> None:
    # Um grupo que alguém criou de raiz é um grupo a sério: vai antes do
    # "Sem grupo", que é onde ficam as chaves partidas.
    assert indice_grupo("GRUPO_NOVO") < indice_grupo("")
    assert rotulo_grupo(None) == "Sem grupo"


def test_blocos_contiguos_nao_reordenam_nada() -> None:
    """As faixas da tabela seguem a coluna Ordem, senão as setas mentiam."""
    linhas = [
        _linha(1, "FERRAGEM_VARAO"),
        _linha(2, "MATERIAL_COSTAS"),
        _linha(3, "FERRAGEM_VARAO"),
    ]

    grupos = agrupar_linhas_contiguas(linhas, METAS)

    # A mesma chave aparece em dois blocos, porque é isso que está na tabela.
    assert [grupo.codigo for grupo in grupos] == [
        "FERRAGENS",
        "MATERIAIS",
        "FERRAGENS",
    ]
    ids = [
        linha.id
        for grupo in grupos
        for chave in grupo.chaves
        for linha in chave.linhas
    ]
    assert ids == [1, 2, 3]


def test_ordenar_poe_a_lista_igual_ao_navegador() -> None:
    """É o que o botão "Agrupar por chave" grava na coluna Ordem."""
    linhas = [
        _linha(1, "ACABAMENTO_FACE_SUP"),
        _linha(2, "FERRAGEM_SUPORTE_LATERAL_VARAO"),
        _linha(3, "FERRAGEM_VARAO", prioridade=2),
        _linha(4, "FERRAGEM_VARAO", prioridade=1),
        _linha(5, "MATERIAL_COSTAS"),
    ]

    ordenadas = ordenar_linhas_por_grupo_e_chave(linhas, METAS)

    assert [linha.id for linha in ordenadas] == [5, 4, 3, 2, 1]


def test_linha_sem_prioridade_vai_depois_das_que_tem() -> None:
    linhas = [
        _linha(1, "FERRAGEM_VARAO", prioridade=None),
        _linha(2, "FERRAGEM_VARAO", prioridade=2),
    ]

    ordenadas = ordenar_linhas_por_grupo_e_chave(linhas, METAS)

    assert [linha.id for linha in ordenadas] == [2, 1]
