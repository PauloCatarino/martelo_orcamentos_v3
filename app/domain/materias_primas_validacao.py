"""Pure validation rules for the raw-materials Excel, run before importing.

The Excel (``TAB_MATERIAS_PRIMAS.xlsm``) is the entry door of every raw material
used in costing, so anything wrong there reaches the budgets silently. These
rules turn the file into a report *before* a single row is written to the
database.

Severity reuses the costing audit vocabulary (``CRÍTICO`` / ``AVISO``) so the
user reads the same words everywhere in the app.

Design notes:

- everything here is pure: no openpyxl, no database, no Qt. The caller reads the
  file (``scripts/import_materias_primas_excel.py``) and feeds ``LinhaExcel``
  objects in;
- ``Ref_LE`` is the synchronisation key and is used all over the budgets, so a
  duplicate is CRÍTICO, never a warning;
- a zero price is only a problem when the material is *not* a free-price one.
  Rows like "PLACAS LIVRES" / "FERRAGEM LIVRE" exist on purpose: they carry no
  price in the catalog and are filled in locally, inside each budget. The
  ``TIPO_PRECO`` column is what tells the two cases apart.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

# O vocabulário do catálogo (tipos de preço, famílias, unidades) vive em
# app.domain.materia_prima_types e é reexportado aqui, para quem já importava
# estes nomes deste módulo continuar a encontrá-los.
from app.domain.materia_prima_types import (
    FAMILIAS_VALIDAS,
    MESES_PRECO_DESATUALIZADO,
    TIPO_PRECO_LIVRE,
    TIPO_PRECO_TABELA,
    TIPOS_PRECO_VALIDOS,
    UNIDADES_VALIDAS,
)

__all__ = [
    "FAMILIAS_VALIDAS",
    "MESES_PRECO_DESATUALIZADO",
    "TIPOS_PRECO_VALIDOS",
    "TIPO_PRECO_LIVRE",
    "TIPO_PRECO_TABELA",
    "UNIDADES_VALIDAS",
    "AvisoExcel",
    "LinhaExcel",
    "RelatorioExcel",
    "resumir",
    "validar_linhas",
]

# Same words as the costing audit (``app.services.custeio_auditoria_service``),
# repeated here on purpose: this module must stay pure (no database, no Qt) so
# it can be tested without opening an Excel file or a session.
CRITICO = "CRÍTICO"
AVISO = "AVISO"
INFO = "INFO"

# Categories (short, stable keys the UI can group by).
CAT_SEM_REF_LE = "sem_ref_le"
CAT_LINHA_VAZIA = "linha_vazia"
CAT_REF_LE_DUPLICADA = "ref_le_duplicada"
CAT_SEM_DESCRICAO = "sem_descricao"
CAT_PRECO_EM_FALTA = "preco_em_falta"
CAT_ORLA_INEXISTENTE = "orla_inexistente"
CAT_ESPESSURA_DIVERGENTE = "espessura_divergente"
CAT_PRECO_DESATUALIZADO = "preco_desatualizado"
CAT_VALOR_FORA_DA_LISTA = "valor_fora_da_lista"
CAT_DESAPARECEU_DO_EXCEL = "desapareceu_do_excel"
CAT_PRECO_ALTERADO = "preco_alterado"
# Table-price differences below this are noise, not a change (same tolerance as
# the ValueSet price sync).
TOLERANCIA_PRECO = Decimal("0.05")

# "AGL ... 19MM" -> 19. Only used for PLACAS, where the thickness is part of the
# commercial description and must agree with ESP_MP.
_PADRAO_ESPESSURA_DESCRICAO = re.compile(r"(\d{1,3})\s*MM\b")


@dataclass(frozen=True)
class LinhaExcel:
    """One data row of the Excel, already converted to Python values."""

    numero: int
    ref_le: str | None = None
    descricao: str | None = None
    familia: str | None = None
    tipo: str | None = None
    unidade: str | None = None
    preco_tabela: Decimal | None = None
    preco_liquido: Decimal | None = None
    espessura: Decimal | None = None
    coresp_orla_0_4: str | None = None
    coresp_orla_1_0: str | None = None
    tipo_preco: str | None = None
    ativo: bool | None = None
    data_ultimo_preco: date | None = None

    @property
    def vazia(self) -> bool:
        """True when the row carries no real content (only dragged formulas)."""
        return not any(
            (
                _texto(self.ref_le),
                _texto(self.descricao),
                _texto(self.familia),
                _texto(self.tipo),
                self.preco_tabela,
                self.espessura,
            )
        )

    @property
    def preco_livre(self) -> bool:
        """True when this material is filled in locally, inside each budget."""
        return _normalizar(self.tipo_preco) == TIPO_PRECO_LIVRE


@dataclass(frozen=True)
class AvisoExcel:
    """One finding about one Excel row (or about one missing material)."""

    severidade: str
    categoria: str
    mensagem: str
    linha: int | None = None
    ref_le: str | None = None
    descricao: str | None = None
    detalhe: str | None = None


@dataclass(frozen=True)
class RelatorioExcel:
    """Full result of validating the workbook."""

    avisos: tuple[AvisoExcel, ...] = ()
    total_linhas: int = 0
    linhas_com_ref_le: int = 0

    @property
    def criticos(self) -> tuple[AvisoExcel, ...]:
        return tuple(a for a in self.avisos if a.severidade == CRITICO)

    @property
    def alertas(self) -> tuple[AvisoExcel, ...]:
        return tuple(a for a in self.avisos if a.severidade == AVISO)

    @property
    def informativos(self) -> tuple[AvisoExcel, ...]:
        return tuple(a for a in self.avisos if a.severidade == INFO)

    @property
    def pode_importar(self) -> bool:
        """True when nothing critical was found."""
        return not self.criticos

    def contagem_por_categoria(self) -> dict[str, int]:
        """How many findings of each category, for the summary line."""
        return dict(Counter(aviso.categoria for aviso in self.avisos))


def validar_linhas(
    linhas: Iterable[LinhaExcel],
    materias_existentes: Iterable[object] = (),
    *,
    hoje: date | None = None,
    meses_preco_desatualizado: int = MESES_PRECO_DESATUALIZADO,
) -> RelatorioExcel:
    """Validate the workbook rows and return the full report.

    ``materias_existentes`` are the raw materials already in the database (any
    object with ``ref_le``, ``preco_tabela`` and ``ativo``). They are only used
    to compare prices and to spot materials that vanished from the Excel; pass
    nothing to validate the file on its own.
    """
    linhas = list(linhas)
    hoje = hoje or date.today()
    avisos: list[AvisoExcel] = []

    refs_existentes = {
        _normalizar(linha.ref_le) for linha in linhas if _texto(linha.ref_le)
    }
    contagem_refs = Counter(
        _normalizar(linha.ref_le) for linha in linhas if _texto(linha.ref_le)
    )
    duplicadas_avisadas: set[str] = set()

    for linha in linhas:
        avisos.extend(
            _validar_linha(
                linha,
                refs_existentes=refs_existentes,
                contagem_refs=contagem_refs,
                duplicadas_avisadas=duplicadas_avisadas,
                hoje=hoje,
                meses_preco_desatualizado=meses_preco_desatualizado,
            )
        )

    avisos.extend(_comparar_com_base_de_dados(linhas, materias_existentes))

    return RelatorioExcel(
        avisos=tuple(avisos),
        total_linhas=len(linhas),
        linhas_com_ref_le=sum(1 for linha in linhas if _texto(linha.ref_le)),
    )


def _validar_linha(
    linha: LinhaExcel,
    *,
    refs_existentes: set[str],
    contagem_refs: Counter,
    duplicadas_avisadas: set[str],
    hoje: date,
    meses_preco_desatualizado: int,
) -> list[AvisoExcel]:
    """Validate one row of the workbook."""
    avisos: list[AvisoExcel] = []
    ref_le = _texto(linha.ref_le)

    if linha.vazia:
        # Rows past the end of the data, kept alive only by the dragged PLIQ
        # formula. Harmless, but they make the table look longer than it is.
        return [
            AvisoExcel(
                severidade=AVISO,
                categoria=CAT_LINHA_VAZIA,
                mensagem="Linha vazia (só a fórmula do PLIQ) — pode ser apagada.",
                linha=linha.numero,
            )
        ]

    if not ref_le:
        avisos.append(
            AvisoExcel(
                severidade=CRITICO,
                categoria=CAT_SEM_REF_LE,
                mensagem="Linha com dados mas sem Ref LE — vai ser ignorada na importação.",
                linha=linha.numero,
                descricao=_texto(linha.descricao),
                detalhe="Use a macro 'Atualizar_ID_e_Ref' para atribuir a referência.",
            )
        )
    else:
        chave = _normalizar(ref_le)
        if contagem_refs[chave] > 1 and chave not in duplicadas_avisadas:
            duplicadas_avisadas.add(chave)
            avisos.append(
                AvisoExcel(
                    severidade=CRITICO,
                    categoria=CAT_REF_LE_DUPLICADA,
                    mensagem=f"Ref LE repetida {contagem_refs[chave]} vezes no Excel.",
                    linha=linha.numero,
                    ref_le=ref_le,
                    descricao=_texto(linha.descricao),
                    detalhe=(
                        "A Ref LE identifica o material em todos os orçamentos e "
                        "não pode repetir-se. Só a última linha ficaria gravada."
                    ),
                )
            )

    if not _texto(linha.descricao):
        avisos.append(
            AvisoExcel(
                severidade=CRITICO,
                categoria=CAT_SEM_DESCRICAO,
                mensagem="Sem descrição — a linha é ignorada na importação.",
                linha=linha.numero,
                ref_le=ref_le,
            )
        )

    avisos.extend(_validar_preco(linha, hoje, meses_preco_desatualizado))
    avisos.extend(_validar_listas(linha))
    avisos.extend(_validar_orlas(linha, refs_existentes))
    avisos.extend(_validar_espessura(linha))

    return avisos


def _validar_preco(
    linha: LinhaExcel, hoje: date, meses_preco_desatualizado: int
) -> list[AvisoExcel]:
    """Check the price itself and how old it is."""
    avisos: list[AvisoExcel] = []
    ref_le = _texto(linha.ref_le)

    if linha.preco_livre:
        # Free-price material: no price here on purpose, and no point in asking
        # when it was last updated.
        return avisos

    if not linha.preco_liquido:
        avisos.append(
            AvisoExcel(
                severidade=CRITICO,
                categoria=CAT_PRECO_EM_FALTA,
                mensagem="Preço líquido a zero — o material entra no custeio a 0,00 €.",
                linha=linha.numero,
                ref_le=ref_le,
                descricao=_texto(linha.descricao),
                detalhe=(
                    "Preencha o PRECO_TABELA, ou marque TIPO_PRECO = LIVRE se o "
                    "preço for para editar dentro de cada orçamento."
                ),
            )
        )
        return avisos

    meses = _meses_desde(linha.data_ultimo_preco, hoje)
    if meses is None:
        avisos.append(
            AvisoExcel(
                severidade=AVISO,
                categoria=CAT_PRECO_DESATUALIZADO,
                mensagem="Sem DATA_ULTIMO_PRECO — não se sabe de quando é o preço.",
                linha=linha.numero,
                ref_le=ref_le,
                descricao=_texto(linha.descricao),
            )
        )
    elif meses >= meses_preco_desatualizado:
        avisos.append(
            AvisoExcel(
                severidade=AVISO,
                categoria=CAT_PRECO_DESATUALIZADO,
                mensagem=f"Preço com {meses} meses — deve ser revisto.",
                linha=linha.numero,
                ref_le=ref_le,
                descricao=_texto(linha.descricao),
                detalhe=f"Último preço em {linha.data_ultimo_preco:%d-%m-%Y}.",
            )
        )

    return avisos


def _validar_listas(linha: LinhaExcel) -> list[AvisoExcel]:
    """Check the classification columns against the accepted values."""
    avisos: list[AvisoExcel] = []
    ref_le = _texto(linha.ref_le)

    familia = _normalizar(linha.familia)
    if familia and familia not in FAMILIAS_VALIDAS:
        avisos.append(
            AvisoExcel(
                severidade=AVISO,
                categoria=CAT_VALOR_FORA_DA_LISTA,
                mensagem=f"FAMILIA '{linha.familia}' fora da lista de valores.",
                linha=linha.numero,
                ref_le=ref_le,
                detalhe="Valores aceites: " + ", ".join(FAMILIAS_VALIDAS) + ".",
            )
        )
    elif not familia:
        avisos.append(
            AvisoExcel(
                severidade=CRITICO,
                categoria=CAT_VALOR_FORA_DA_LISTA,
                mensagem="Sem FAMILIA — a macro não consegue atribuir a Ref LE.",
                linha=linha.numero,
                ref_le=ref_le,
                descricao=_texto(linha.descricao),
            )
        )

    unidade = _normalizar(linha.unidade)
    if unidade and unidade not in UNIDADES_VALIDAS:
        avisos.append(
            AvisoExcel(
                severidade=AVISO,
                categoria=CAT_VALOR_FORA_DA_LISTA,
                mensagem=f"UND '{linha.unidade}' fora da lista de valores.",
                linha=linha.numero,
                ref_le=ref_le,
                detalhe="Valores aceites: " + ", ".join(UNIDADES_VALIDAS) + ".",
            )
        )

    tipo_preco = _normalizar(linha.tipo_preco)
    if tipo_preco and tipo_preco not in TIPOS_PRECO_VALIDOS:
        avisos.append(
            AvisoExcel(
                severidade=AVISO,
                categoria=CAT_VALOR_FORA_DA_LISTA,
                mensagem=f"TIPO_PRECO '{linha.tipo_preco}' fora da lista de valores.",
                linha=linha.numero,
                ref_le=ref_le,
                detalhe="Valores aceites: " + ", ".join(TIPOS_PRECO_VALIDOS) + ".",
            )
        )

    return avisos


def _validar_orlas(linha: LinhaExcel, refs_existentes: set[str]) -> list[AvisoExcel]:
    """Check that the edge-banding references point to real materials."""
    avisos: list[AvisoExcel] = []

    for coluna, valor in (
        ("CORESP_ORLA_0_4", linha.coresp_orla_0_4),
        ("CORESP_ORLA_1_0", linha.coresp_orla_1_0),
    ):
        referencia = _texto(valor)
        if referencia and _normalizar(referencia) not in refs_existentes:
            avisos.append(
                AvisoExcel(
                    severidade=CRITICO,
                    categoria=CAT_ORLA_INEXISTENTE,
                    mensagem=f"{coluna} aponta para '{referencia}', que não existe.",
                    linha=linha.numero,
                    ref_le=_texto(linha.ref_le),
                    descricao=_texto(linha.descricao),
                    detalhe="A orla não é calculada e o custo sai por baixo.",
                )
            )

    return avisos


def _validar_espessura(linha: LinhaExcel) -> list[AvisoExcel]:
    """For panels, the thickness in the description must match ESP_MP."""
    if _normalizar(linha.familia) != "PLACAS" or linha.espessura is None:
        return []

    descricao = _texto(linha.descricao)
    if not descricao:
        return []

    encontrado = _PADRAO_ESPESSURA_DESCRICAO.search(descricao.upper())
    if encontrado is None:
        return []

    espessura_descricao = Decimal(encontrado.group(1))
    if espessura_descricao == linha.espessura:
        return []

    return [
        AvisoExcel(
            severidade=AVISO,
            categoria=CAT_ESPESSURA_DIVERGENTE,
            mensagem=(
                f"A descrição diz {espessura_descricao}MM mas ESP_MP é "
                f"{linha.espessura}."
            ),
            linha=linha.numero,
            ref_le=_texto(linha.ref_le),
            descricao=descricao,
            detalhe="A espessura errada propaga-se ao custeio e ao plano de corte.",
        )
    ]


def _comparar_com_base_de_dados(
    linhas: list[LinhaExcel], materias_existentes: Iterable[object]
) -> list[AvisoExcel]:
    """Compare the workbook against what is already in the database."""
    avisos: list[AvisoExcel] = []
    por_ref = {
        _normalizar(linha.ref_le): linha for linha in linhas if _texto(linha.ref_le)
    }

    for materia in materias_existentes:
        ref_le = _texto(getattr(materia, "ref_le", None))
        if not ref_le:
            continue

        linha = por_ref.get(_normalizar(ref_le))

        if linha is None:
            if getattr(materia, "ativo", True):
                avisos.append(
                    AvisoExcel(
                        severidade=AVISO,
                        categoria=CAT_DESAPARECEU_DO_EXCEL,
                        mensagem="Existe no Martelo mas já não está no Excel.",
                        ref_le=ref_le,
                        descricao=_texto(getattr(materia, "descricao", None)),
                        detalhe=(
                            "Continua a aparecer nas escolhas. Reponha a linha no "
                            "Excel ou marque ATIVO = NAO."
                        ),
                    )
                )
            continue

        preco_guardado = getattr(materia, "preco_tabela", None)
        preco_novo = linha.preco_tabela
        if (
            preco_guardado is not None
            and preco_novo is not None
            and abs(Decimal(preco_guardado) - preco_novo) > TOLERANCIA_PRECO
        ):
            avisos.append(
                AvisoExcel(
                    severidade=INFO,
                    categoria=CAT_PRECO_ALTERADO,
                    mensagem=(
                        f"Preço de tabela alterado: {preco_guardado} € → {preco_novo} €."
                    ),
                    linha=linha.numero,
                    ref_le=ref_le,
                    descricao=_texto(linha.descricao),
                    detalhe=(
                        "A importação atualiza o catálogo; os orçamentos já feitos "
                        "mantêm o preço com que foram calculados."
                    ),
                )
            )

    return avisos


def _texto(valor: object) -> str | None:
    """Trimmed text, or None when empty."""
    if valor is None:
        return None

    texto = str(valor).strip()
    return texto or None


def _normalizar(valor: object) -> str:
    """Upper-case, accent-free, trimmed text for comparisons."""
    texto = _texto(valor)
    if texto is None:
        return ""

    decomposto = unicodedata.normalize("NFKD", texto)
    sem_acentos = "".join(c for c in decomposto if not unicodedata.combining(c))
    return sem_acentos.upper()


def _meses_desde(valor: date | datetime | None, hoje: date) -> int | None:
    """Whole months between a date and today, or None when there is no date."""
    if valor is None:
        return None

    if isinstance(valor, datetime):
        valor = valor.date()

    meses = (hoje.year - valor.year) * 12 + (hoje.month - valor.month)
    if hoje.day < valor.day:
        meses -= 1

    return max(meses, 0)


def resumir(relatorio: RelatorioExcel) -> str:
    """One-line, user-facing summary of the report."""
    if not relatorio.avisos:
        return (
            f"Excel verificado: {relatorio.total_linhas} linhas, "
            "nenhum problema encontrado."
        )

    partes = []
    if relatorio.criticos:
        partes.append(f"{len(relatorio.criticos)} críticos")
    if relatorio.alertas:
        partes.append(f"{len(relatorio.alertas)} avisos")
    if relatorio.informativos:
        partes.append(f"{len(relatorio.informativos)} informativos")

    return (
        f"Excel verificado: {relatorio.total_linhas} linhas — " + ", ".join(partes) + "."
    )
