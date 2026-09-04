"""A reparação dos módulos só toca na forma exata que o bug deixou.

O bug da importação deixava uma peça SIMPLES sozinha, com todos os filhos por
baixo dela desaparecidos de uma vez. É essa forma — e só essa — que se repõe.
Comparar tudo com o catálogo de hoje daria falsos positivos nos módulos
antigos, cuja estrutura é anterior a mudanças no catálogo.
"""

from __future__ import annotations

import importlib.util
import sys
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models import (
    DefModulo,
    DefModuloLinha,
    DefPeca,
    DefPecaComponente,
)

RAIZ = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "reparar_associados_modulos", RAIZ / "scripts" / "reparar_associados_modulos.py"
)
reparar_modulo = importlib.util.module_from_spec(_spec)
# O @dataclass do script vai buscar o módulo ao sys.modules enquanto o constrói.
sys.modules[_spec.name] = reparar_modulo
_spec.loader.exec_module(reparar_modulo)


@pytest.fixture()
def catalogo(session: Session):
    """Um teto que leva duas uniões, e uma composta porta+dobradiça."""
    teto = DefPeca(codigo="TETO_2000", nome="Teto[2000]", ativo=True)
    uniao = DefPeca(codigo="SISTEMAS_UNIAO", nome="Sistemas Uniao", ativo=True)
    composta = DefPeca(codigo="PORTA+DOBR", nome="Porta+Dobradiça", ativo=True)
    porta = DefPeca(codigo="PORTA_SIMPLES", nome="Porta simples", ativo=True)
    session.add_all([teto, uniao, composta, porta])
    session.flush()

    session.add_all(
        [
            DefPecaComponente(
                def_peca_pai_id=teto.id,
                tipo_componente="FERRAGEM",
                def_peca_componente_id=uniao.id,
                ordem=1,
                quantidade=Decimal("1"),
                ativo=True,
            ),
            DefPecaComponente(
                def_peca_pai_id=teto.id,
                tipo_componente="FERRAGEM",
                def_peca_componente_id=uniao.id,
                ordem=2,
                quantidade=Decimal("1"),
                ativo=True,
            ),
            DefPecaComponente(
                def_peca_pai_id=composta.id,
                tipo_componente="PECA",
                def_peca_componente_id=porta.id,
                ordem=1,
                quantidade=Decimal("1"),
                ativo=True,
            ),
        ]
    )
    session.flush()
    return {"teto": teto, "uniao": uniao, "composta": composta, "porta": porta}


def _modulo(session, codigo, linhas) -> DefModulo:
    modulo = DefModulo(codigo=codigo, nome=codigo, ativo=True)
    session.add(modulo)
    session.flush()
    for dados in linhas:
        session.add(DefModuloLinha(def_modulo_id=modulo.id, ativo=True, **dados))
    session.flush()
    return modulo


def test_repoe_as_unioes_de_uma_peca_simples_que_ficou_sozinha(
    session: Session, catalogo
) -> None:
    _modulo(
        session,
        "MOD_PARTIDO",
        [
            dict(
                ordem=1,
                tipo_linha="PECA",
                def_peca_id=catalogo["teto"].id,
                def_peca_codigo="TETO_2000",
                qt_mod="1",
                qt_und="1",
                nivel=0,
            )
        ],
    )

    planos = reparar_modulo._analisar(session, None)

    assert len(planos) == 1
    assert [f.codigo_filho for f in planos[0].faltas] == [
        "SISTEMAS_UNIAO",
        "SISTEMAS_UNIAO",
    ]

    reparar_modulo._aplicar(session, "MOD_PARTIDO", planos[0])
    session.flush()

    linhas = session.execute(
        select(DefModuloLinha).order_by(DefModuloLinha.ordem)
    ).scalars().all()
    assert [(l.def_peca_codigo, l.ordem, l.linha_pai_ordem, l.nivel) for l in linhas] == [
        ("TETO_2000", 1, None, 0),
        ("SISTEMAS_UNIAO", 2, 1, 1),
        ("SISTEMAS_UNIAO", 3, 1, 1),
    ]
    # Correr outra vez não acrescenta nada.
    assert reparar_modulo._analisar(session, None) == []


def test_nao_mexe_numa_peca_que_ja_tem_filhos_guardados(
    session: Session, catalogo
) -> None:
    """Estrutura antiga não é estrutura partida: comparar com o catálogo de hoje
    daria um falso positivo."""
    _modulo(
        session,
        "MOD_ANTIGO",
        [
            dict(
                ordem=1,
                tipo_linha="PECA",
                def_peca_id=catalogo["teto"].id,
                def_peca_codigo="TETO_2000",
                qt_mod="1",
                qt_und="1",
                nivel=0,
            ),
            dict(
                ordem=2,
                tipo_linha="FERRAGEM",
                def_peca_id=catalogo["uniao"].id,
                def_peca_codigo="SISTEMAS_UNIAO",
                qt_mod="1",
                qt_und="8",
                linha_pai_ordem=1,
                nivel=1,
            ),
        ],
    )

    assert reparar_modulo._analisar(session, None) == []


def test_nao_mexe_numa_composta_sem_filhos_guardados(
    session: Session, catalogo
) -> None:
    """Uma composta sem filhos re-expande-se inteira do catálogo na importação."""
    _modulo(
        session,
        "MOD_COMPOSTA",
        [
            dict(
                ordem=1,
                tipo_linha="PECA_COMPOSTA",
                def_peca_id=catalogo["composta"].id,
                def_peca_codigo="PORTA+DOBR",
                qt_mod="1",
                qt_und="1",
                nivel=0,
            )
        ],
    )

    assert reparar_modulo._analisar(session, None) == []
