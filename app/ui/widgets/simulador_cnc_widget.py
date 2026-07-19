"""Interactive CNC/coating cost simulator (mirror of the approved HTML model).

One reusable widget: máquina → método → dynamic fields → live formula and STD
vs SÉRIE costs, with preloaded scenarios. It lives as the "Simulador" tab of
the Operações/Máquinas/Simulador page and, wrapped in ``SimuladorCncDialog``,
opens prefilled from the operation dialogs and the costing table. All costs
come from the SAME pure domain dispatcher the engine uses, so the simulated
value always matches the production cost.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.domain.custo_cnc_metodo import (
    TarifasCncMaquina,
    calcular_custo_cnc_por_metodo,
)
from app.domain.custo_producao import escolher_tarifa, selecionar_escalao_area
from app.domain.medidas import normalizar_numero
from app.domain import metodo_calculo_types as metodo_types
from app.utils.formatters import format_currency, format_quantity

_D = Decimal


@dataclass(frozen=True)
class MaquinaSimulacao:
    """Machine data the simulator needs (decoupled from the DB read model)."""

    codigo: str
    nome: str
    tipo: str = "CNC"
    custo_hora_std: Decimal | None = None
    custo_hora_serie: Decimal | None = None
    preco_furo_std: Decimal | None = None
    preco_furo_serie: Decimal | None = None
    preco_rasgo_ml_std: Decimal | None = None
    preco_rasgo_ml_serie: Decimal | None = None
    preco_m2_face_std: Decimal | None = None
    preco_m2_face_serie: Decimal | None = None
    permite_escaloes_area: bool = False
    permite_furacao: bool = False
    permite_rasgos: bool = False
    permite_pocket: bool = False
    escaloes: tuple = field(default_factory=tuple)

    def tarifas(self, usar_serie: bool) -> TarifasCncMaquina:
        preco_rasgo, _ = escolher_tarifa(
            self.preco_rasgo_ml_std, self.preco_rasgo_ml_serie, usar_serie
        )
        preco_furo, _ = escolher_tarifa(
            self.preco_furo_std, self.preco_furo_serie, usar_serie
        )
        custo_hora, _ = escolher_tarifa(
            self.custo_hora_std, self.custo_hora_serie, usar_serie
        )
        preco_face, _ = escolher_tarifa(
            self.preco_m2_face_std, self.preco_m2_face_serie, usar_serie
        )
        return TarifasCncMaquina(
            escaloes_ativos=self.escaloes,
            preco_rasgo_ml=preco_rasgo,
            preco_furo=preco_furo,
            custo_hora=custo_hora,
            preco_m2_face=preco_face,
            permite_escaloes_area=self.permite_escaloes_area,
            permite_rasgos=self.permite_rasgos,
            permite_furacao=self.permite_furacao,
        )


def carregar_maquinas_simulacao() -> list[MaquinaSimulacao]:
    """Load the active CNC/coating machines (+ tiers) from the database."""
    from app.db.session import SessionLocal
    from app.repositories.def_maquina_escalao_area_repository import (
        DefMaquinaEscalaoAreaRepository,
    )
    from app.services.def_maquina_service import DefMaquinaService

    maquinas: list[MaquinaSimulacao] = []
    with SessionLocal() as session:
        escaloes_repo = DefMaquinaEscalaoAreaRepository(session)
        for maquina in DefMaquinaService(session).listar_maquinas_ativas():
            tipo = (maquina.tipo or "").strip().upper()
            if tipo not in ("CNC", metodo_types.REVESTIMENTO):
                continue
            maquinas.append(
                MaquinaSimulacao(
                    codigo=maquina.codigo,
                    nome=maquina.nome,
                    tipo=tipo,
                    custo_hora_std=maquina.custo_hora,
                    custo_hora_serie=maquina.custo_hora_serie,
                    preco_furo_std=maquina.preco_furo_std,
                    preco_furo_serie=maquina.preco_furo_serie,
                    preco_rasgo_ml_std=maquina.preco_rasgo_ml_std,
                    preco_rasgo_ml_serie=maquina.preco_rasgo_ml_serie,
                    preco_m2_face_std=maquina.preco_m2_face_std,
                    preco_m2_face_serie=maquina.preco_m2_face_serie,
                    permite_escaloes_area=maquina.permite_escaloes_area,
                    permite_furacao=maquina.permite_furacao,
                    permite_rasgos=maquina.permite_rasgos,
                    permite_pocket=maquina.permite_pocket,
                    escaloes=tuple(
                        escaloes_repo.list_active_by_maquina(maquina.id)
                    ),
                )
            )
    return maquinas


@dataclass
class _OperacaoSimulada:
    maquina: MaquinaSimulacao
    metodo: str
    params: dict


class SimuladorCncWidget(QWidget):
    """Live simulator: pick machine + method, fill the method fields, compare
    the STD and SÉRIE costs of every operation added to the piece."""

    OPS_HEADERS = [
        "Máquina",
        "Método",
        "Parâmetros",
        "Fórmula (modo ativo)",
        "Custo STD",
        "Custo SÉRIE",
        "",
    ]

    def __init__(
        self,
        maquinas: list[MaquinaSimulacao] | None = None,
        parent=None,
        mostrar_cenarios: bool = True,
    ) -> None:
        super().__init__(parent)
        self._maquinas = list(maquinas or [])
        self._operacoes: list[_OperacaoSimulada] = []

        intro = QLabel(
            "Escolha a máquina e o método de cálculo, preencha só os campos "
            "desse método e veja o custo com a fórmula aberta. Os totais STD "
            "e SÉRIE aparecem sempre lado a lado. As tarifas vêm das máquinas "
            "reais das Configurações."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #666;")

        # --- Piece under analysis -------------------------------------------
        peca_box = QGroupBox("Peça em análise")
        self.comp_input = QLineEdit("600")
        self.comp_input.setToolTip("Comprimento real da peça (mm).")
        self.larg_input = QLineEdit("400")
        self.larg_input.setToolTip("Largura real da peça (mm).")
        self.qt_input = QSpinBox()
        self.qt_input.setRange(1, 99999)
        self.qt_input.setValue(1)
        self.qt_input.setToolTip("Quantidade total de peças.")
        self.modo_input = QComboBox()
        self.modo_input.addItem("STD (peça única)", "STD")
        self.modo_input.addItem("SÉRIE (lote)", "SERIE")
        self.modo_input.setToolTip(
            "Modo ativo (destacado nos totais). Tarifa SÉRIE vazia recorre à "
            "STD (regra da aplicação)."
        )
        self.area_label = QLabel("—")
        peca_layout = QGridLayout(peca_box)
        peca_layout.addWidget(QLabel("Comprimento (mm)"), 0, 0)
        peca_layout.addWidget(self.comp_input, 0, 1)
        peca_layout.addWidget(QLabel("Largura (mm)"), 0, 2)
        peca_layout.addWidget(self.larg_input, 0, 3)
        peca_layout.addWidget(QLabel("Quantidade"), 0, 4)
        peca_layout.addWidget(self.qt_input, 0, 5)
        peca_layout.addWidget(QLabel("Modo"), 1, 0)
        peca_layout.addWidget(self.modo_input, 1, 1)
        peca_layout.addWidget(QLabel("Área (m²)"), 1, 2)
        peca_layout.addWidget(self.area_label, 1, 3)

        # --- Add-operation form ---------------------------------------------
        op_box = QGroupBox("Adicionar operação")
        self.maquina_input = QComboBox()
        self.maquina_input.setToolTip("Máquina CNC ou de revestimento.")
        self.metodo_input = QComboBox()
        self.metodo_input.setToolTip(
            "Métodos permitidos pela máquina escolhida (capacidades)."
        )
        self.metodo_ajuda = QLabel("")
        self.metodo_ajuda.setWordWrap(True)
        self.metodo_ajuda.setStyleSheet("color: #666; font-size: 11px;")

        # Dynamic method fields (visibility switches with the method).
        self.setup_min_input = self._spin(" min", 0, 9999, 1)
        self.min_unidade_input = self._spin(" min", 0, 9999, 2)
        self.unidades_input = QSpinBox()
        self.unidades_input.setRange(1, 9999)
        self.furos_input = QSpinBox()
        self.furos_input.setRange(1, 999)
        self.furos_input.setValue(3)
        self.rasgo_comp_input = QSpinBox()
        self.rasgo_comp_input.setRange(0, 99)
        self.rasgo_comp_input.setValue(1)
        self.rasgo_larg_input = QSpinBox()
        self.rasgo_larg_input.setRange(0, 99)
        self.faces_input = QComboBox()
        self.faces_input.addItem("1 face", 1)
        self.faces_input.addItem("2 faces", 2)
        self.faces_input.setCurrentIndex(1)

        self._campos_metodo: dict[str, list[tuple[QLabel, QWidget]]] = {
            metodo_types.TEMPO: [
                (QLabel("Setup (min)"), self.setup_min_input),
                (QLabel("Min/unidade"), self.min_unidade_input),
                (QLabel("N.º unidades"), self.unidades_input),
            ],
            metodo_types.FURACAO: [
                (QLabel("Furos por unidade"), self.furos_input),
            ],
            metodo_types.RASGO: [
                (QLabel("N.º rasgos ao comprimento"), self.rasgo_comp_input),
                (QLabel("N.º rasgos à largura"), self.rasgo_larg_input),
            ],
            metodo_types.REVESTIMENTO: [
                (QLabel("N.º de faces"), self.faces_input),
            ],
        }

        self.adicionar_button = QPushButton("Adicionar operação")
        self.adicionar_button.setToolTip(
            "Acrescenta a operação à peça; os custos somam-se."
        )
        self.limpar_button = QPushButton("Limpar")
        self.limpar_button.setToolTip("Remove todas as operações simuladas.")

        op_layout = QGridLayout(op_box)
        op_layout.addWidget(QLabel("Máquina"), 0, 0)
        op_layout.addWidget(self.maquina_input, 0, 1)
        op_layout.addWidget(QLabel("Método"), 0, 2)
        op_layout.addWidget(self.metodo_input, 0, 3)
        op_layout.addWidget(self.adicionar_button, 0, 4)
        op_layout.addWidget(self.limpar_button, 0, 5)
        # Dynamic method fields share one row; hidden ones take no space.
        campos_layout = QHBoxLayout()
        for widgets in self._campos_metodo.values():
            for label, widget in widgets:
                campos_layout.addWidget(label)
                campos_layout.addWidget(widget)
        campos_layout.addStretch()
        op_layout.addLayout(campos_layout, 1, 0, 1, 6)
        op_layout.addWidget(self.metodo_ajuda, 2, 0, 1, 6)

        # --- Operations table + totals --------------------------------------
        self.ops_table = QTableWidget(0, len(self.OPS_HEADERS))
        self.ops_table.setHorizontalHeaderLabels(self.OPS_HEADERS)
        self.ops_table.verticalHeader().setVisible(False)
        self.ops_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.ops_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch
        )

        self.totais_label = QLabel("")
        self.totais_label.setObjectName("simuladorCncTotais")
        self.totais_label.setStyleSheet(
            "background-color: #efebe9; border-radius: 6px; padding: 8px; "
            "font-weight: bold;"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.addWidget(intro)
        layout.addWidget(peca_box)
        layout.addWidget(op_box)
        if mostrar_cenarios:
            layout.addLayout(self._criar_cenarios())
        layout.addWidget(self.ops_table, stretch=1)
        layout.addWidget(self.totais_label)

        self.maquina_input.currentIndexChanged.connect(self._atualizar_metodos)
        self.metodo_input.currentIndexChanged.connect(self._atualizar_campos_metodo)
        self.adicionar_button.clicked.connect(self._adicionar_do_formulario)
        self.limpar_button.clicked.connect(self.limpar_operacoes)
        self.modo_input.currentIndexChanged.connect(self._recalcular)
        self.qt_input.valueChanged.connect(self._recalcular)
        self.comp_input.textChanged.connect(self._recalcular)
        self.larg_input.textChanged.connect(self._recalcular)
        self.ops_table.cellClicked.connect(self._remover_se_botao)

        self._preencher_maquinas()
        self._recalcular()

    # ------------------------------------------------------------------ API
    def definir_maquinas(self, maquinas: list[MaquinaSimulacao]) -> None:
        self._maquinas = list(maquinas)
        self._preencher_maquinas()
        self._recalcular()

    def definir_peca(
        self, comp, larg, qt=None, usar_serie: bool | None = None
    ) -> None:
        """Prefill the piece under analysis (e.g. from a costing line)."""
        if comp is not None:
            self.comp_input.setText(self._fmt_num(comp))
        if larg is not None:
            self.larg_input.setText(self._fmt_num(larg))
        if qt is not None:
            try:
                self.qt_input.setValue(max(1, int(Decimal(str(qt)))))
            except (InvalidOperation, ValueError):
                pass
        if usar_serie is not None:
            self.modo_input.setCurrentIndex(1 if usar_serie else 0)

    def limpar_operacoes(self) -> None:
        self._operacoes = []
        self._recalcular()

    def adicionar_operacao(
        self, maquina_codigo: str, metodo: str, **params
    ) -> bool:
        """Add one operation programmatically (prefill from dialogs)."""
        maquina = next(
            (m for m in self._maquinas if m.codigo == maquina_codigo), None
        )
        normalizado = metodo_types.normalize_metodo_calculo(metodo)
        if (
            maquina is None
            or normalizado is None
            or normalizado
            not in metodo_types.metodos_disponiveis_para_maquina(maquina)
        ):
            return False
        self._operacoes.append(
            _OperacaoSimulada(maquina=maquina, metodo=normalizado, params=params)
        )
        indice = self.maquina_input.findData(maquina_codigo)
        if indice >= 0:
            self.maquina_input.setCurrentIndex(indice)
        self._recalcular()
        return True

    # ------------------------------------------------------------- internals
    @staticmethod
    def _spin(sufixo: str, minimo: int, maximo: int, decimais: int) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(minimo, maximo)
        spin.setDecimals(decimais)
        spin.setSuffix(sufixo)
        return spin

    def _criar_cenarios(self) -> QHBoxLayout:
        cenarios = (
            ("Dobradiça (3 furos)", self._cenario_dobradica),
            ("Calha LED (rasgo)", self._cenario_calha),
            ("Pocket 4 min", self._cenario_pocket),
            ("Escalão de área", self._cenario_escalao),
            ("Sandwich 1 face", lambda: self._cenario_sandwich(1)),
            ("Sandwich 2 faces", lambda: self._cenario_sandwich(2)),
            ("Furação + rasgo", self._cenario_furacao_rasgo),
        )
        linha = QHBoxLayout()
        linha.addWidget(QLabel("Cenários:"))
        for rotulo, handler in cenarios:
            botao = QPushButton(rotulo)
            botao.setToolTip("Carrega um exemplo pronto a explorar.")
            botao.clicked.connect(handler)
            linha.addWidget(botao)
        linha.addStretch()
        return linha

    def _maquina_cenario(self, *codigos: str) -> str | None:
        for codigo in codigos:
            if any(m.codigo == codigo for m in self._maquinas):
                return codigo
        return self._maquinas[0].codigo if self._maquinas else None

    def _cenario_dobradica(self) -> None:
        maquina = self._maquina_cenario("CNC_ABD", "CNC_VERTICAL")
        if maquina is None:
            return
        self.limpar_operacoes()
        self.definir_peca(_D("700"), _D("450"), 4, usar_serie=False)
        self.adicionar_operacao(maquina, metodo_types.FURACAO, furos=3)

    def _cenario_calha(self) -> None:
        maquina = self._maquina_cenario("CNC_VERTICAL", "CNC_5_EIXOS")
        if maquina is None:
            return
        self.limpar_operacoes()
        self.definir_peca(_D("1200"), _D("80"), 1, usar_serie=False)
        self.adicionar_operacao(maquina, metodo_types.RASGO, n_comp=1, n_larg=0)

    def _cenario_pocket(self) -> None:
        maquina = self._maquina_cenario("CNC_VERTICAL", "CNC_5_EIXOS")
        if maquina is None:
            return
        self.limpar_operacoes()
        self.definir_peca(_D("500"), _D("300"), 1, usar_serie=False)
        self.adicionar_operacao(
            maquina,
            metodo_types.TEMPO,
            setup=_D("0"),
            min_unidade=_D("4"),
            unidades=1,
        )

    def _cenario_escalao(self) -> None:
        maquina = self._maquina_cenario("CNC_VERTICAL")
        if maquina is None:
            return
        self.limpar_operacoes()
        self.definir_peca(_D("600"), _D("400"), 10, usar_serie=False)
        self.adicionar_operacao(maquina, metodo_types.ESCALAO_AREA)

    def _cenario_sandwich(self, faces: int) -> None:
        maquina = self._maquina_cenario("REVESTIMENTO_SANDWICH")
        if maquina is None:
            return
        self.limpar_operacoes()
        self.definir_peca(_D("2000"), _D("1000"), 1, usar_serie=False)
        self.adicionar_operacao(maquina, metodo_types.REVESTIMENTO, faces=faces)

    def _cenario_furacao_rasgo(self) -> None:
        maquina = self._maquina_cenario("CNC_VERTICAL")
        if maquina is None:
            return
        self.limpar_operacoes()
        self.definir_peca(_D("800"), _D("600"), 2, usar_serie=False)
        self.adicionar_operacao(maquina, metodo_types.FURACAO, furos=8)
        self.adicionar_operacao(maquina, metodo_types.RASGO, n_comp=0, n_larg=1)

    def _preencher_maquinas(self) -> None:
        self.maquina_input.blockSignals(True)
        self.maquina_input.clear()
        for maquina in self._maquinas:
            self.maquina_input.addItem(
                f"{maquina.nome} ({maquina.codigo})", maquina.codigo
            )
        self.maquina_input.blockSignals(False)
        self._atualizar_metodos()

    def _maquina_selecionada(self) -> MaquinaSimulacao | None:
        codigo = self.maquina_input.currentData()
        return next((m for m in self._maquinas if m.codigo == codigo), None)

    def _atualizar_metodos(self) -> None:
        maquina = self._maquina_selecionada()
        metodos = metodo_types.metodos_disponiveis_para_maquina(maquina)
        atual = self.metodo_input.currentData()
        self.metodo_input.blockSignals(True)
        self.metodo_input.clear()
        for metodo in metodos:
            self.metodo_input.addItem(
                metodo_types.METODO_CALCULO_LABELS[metodo], metodo
            )
        indice = self.metodo_input.findData(atual)
        if indice >= 0:
            self.metodo_input.setCurrentIndex(indice)
        self.metodo_input.blockSignals(False)
        self._atualizar_campos_metodo()

    _AJUDA_METODO = {
        metodo_types.ESCALAO_AREA: (
            "Preço por peça escolhido pelo escalão onde cai a área da peça. "
            "Sem campos a preencher."
        ),
        metodo_types.TEMPO: (
            "Custo = (setup + min/unidade × n.º unidades × QT) ÷ 60 × "
            "custo/hora da máquina. Pocket usa este método."
        ),
        metodo_types.FURACAO: (
            "Custo = furos por unidade × QT × €/furo da máquina."
        ),
        metodo_types.RASGO: (
            "ML = (n.º comprimentos × COMP + n.º larguras × LARG) ÷ 1000; "
            "custo = ML × QT × €/ML de rasgo."
        ),
        metodo_types.REVESTIMENTO: (
            "Custo = área (m²) × n.º de faces × QT × €/m² por face."
        ),
    }

    def _atualizar_campos_metodo(self) -> None:
        metodo = self.metodo_input.currentData()
        for chave, widgets in self._campos_metodo.items():
            visivel = chave == metodo
            for label, widget in widgets:
                label.setVisible(visivel)
                widget.setVisible(visivel)
        self.metodo_ajuda.setText(self._AJUDA_METODO.get(metodo, ""))

    def _adicionar_do_formulario(self) -> None:
        maquina = self._maquina_selecionada()
        metodo = self.metodo_input.currentData()
        if maquina is None or metodo is None:
            return
        params: dict = {}
        if metodo == metodo_types.TEMPO:
            params = {
                "setup": _D(str(self.setup_min_input.value())),
                "min_unidade": _D(str(self.min_unidade_input.value())),
                "unidades": self.unidades_input.value(),
            }
        elif metodo == metodo_types.FURACAO:
            params = {"furos": self.furos_input.value()}
        elif metodo == metodo_types.RASGO:
            params = {
                "n_comp": self.rasgo_comp_input.value(),
                "n_larg": self.rasgo_larg_input.value(),
            }
        elif metodo == metodo_types.REVESTIMENTO:
            params = {"faces": self.faces_input.currentData()}
        self._operacoes.append(
            _OperacaoSimulada(maquina=maquina, metodo=metodo, params=params)
        )
        self._recalcular()

    def _remover_se_botao(self, row: int, column: int) -> None:
        if column == len(self.OPS_HEADERS) - 1 and 0 <= row < len(self._operacoes):
            del self._operacoes[row]
            self._recalcular()

    # ------------------------------------------------------------ calculation
    def _peca(self) -> dict:
        comp = self._parse(self.comp_input.text()) or _D("0")
        larg = self._parse(self.larg_input.text()) or _D("0")
        return {
            "comp": comp,
            "larg": larg,
            "qt": _D(self.qt_input.value()),
            "area": comp * larg / _D("1000000"),
        }

    def _custo_operacao(
        self, operacao: _OperacaoSimulada, peca: dict, usar_serie: bool
    ) -> tuple[Decimal | None, str]:
        params = operacao.params
        quantidade_base = None
        rasgo_comp = 0
        rasgo_larg = 0
        setup = None
        min_unidade = None
        if operacao.metodo == metodo_types.TEMPO:
            quantidade_base = _D(str(params.get("unidades", 1)))
            setup = normalizar_numero(params.get("setup"))
            min_unidade = normalizar_numero(params.get("min_unidade"))
        elif operacao.metodo == metodo_types.FURACAO:
            quantidade_base = _D(str(params.get("furos", 0)))
        elif operacao.metodo == metodo_types.RASGO:
            rasgo_comp = int(params.get("n_comp", 0))
            rasgo_larg = int(params.get("n_larg", 0))
        elif operacao.metodo == metodo_types.REVESTIMENTO:
            quantidade_base = _D(str(params.get("faces", 1)))

        custo, _tempo, motivo = calcular_custo_cnc_por_metodo(
            metodo=operacao.metodo,
            area_m2=peca["area"],
            comp_real=peca["comp"],
            larg_real=peca["larg"],
            qt_total=peca["qt"],
            quantidade_base=quantidade_base,
            rasgo_qt_comp=rasgo_comp,
            rasgo_qt_larg=rasgo_larg,
            tempo_setup_minutos=setup,
            tempo_por_unidade_minutos=min_unidade,
            unidade_tempo="PECA",
            tarifas=operacao.maquina.tarifas(usar_serie),
            usar_serie=usar_serie,
        )
        if custo is None:
            return None, self._texto_motivo(motivo)
        return custo, self._texto_formula(operacao, peca, usar_serie, custo)

    @staticmethod
    def _texto_motivo(motivo: str | None) -> str:
        textos = {
            "SEM_TARIFA": "Sem tarifa definida na máquina para este método.",
            "SEM_DADOS": "Faltam dados (medidas ou parâmetros do método).",
            "SEM_ESCALOES": "Máquina sem escalões de área configurados.",
            "MAQUINA_INCOMPATIVEL": "A máquina não permite este método.",
        }
        return textos.get(motivo or "", "Sem custo.")

    def _texto_formula(
        self,
        operacao: _OperacaoSimulada,
        peca: dict,
        usar_serie: bool,
        custo: Decimal,
    ) -> str:
        params = operacao.params
        tarifas = operacao.maquina.tarifas(usar_serie)
        qt = peca["qt"]
        if operacao.metodo == metodo_types.ESCALAO_AREA:
            escalao = selecionar_escalao_area(tarifas.escaloes_ativos, peca["area"])
            preco, _ = escolher_tarifa(
                getattr(escalao, "preco_peca_std", None),
                getattr(escalao, "preco_peca_serie", None),
                usar_serie,
            )
            limite = getattr(escalao, "area_max_m2", None)
            rotulo = (
                f"até {format_quantity(limite)} m²"
                if limite is not None
                else "sem limite"
            )
            return (
                f"área {format_quantity(peca['area'])} m² → escalão {rotulo}: "
                f"{format_currency(preco)}/peça × {format_quantity(qt)} un = "
                f"{format_currency(custo)}"
            )
        if operacao.metodo == metodo_types.TEMPO:
            setup = normalizar_numero(params.get("setup")) or _D("0")
            minutos = normalizar_numero(params.get("min_unidade")) or _D("0")
            unidades = _D(str(params.get("unidades", 1)))
            total = setup + minutos * unidades * qt
            return (
                f"({format_quantity(setup)} min setup + "
                f"{format_quantity(minutos)} min × {format_quantity(unidades)} "
                f"un × {format_quantity(qt)} QT) = {format_quantity(total)} min "
                f"÷ 60 × {format_currency(tarifas.custo_hora)}/h = "
                f"{format_currency(custo)}"
            )
        if operacao.metodo == metodo_types.FURACAO:
            furos = params.get("furos", 0)
            return (
                f"{furos} furos/un × {format_quantity(qt)} un × "
                f"{format_currency(tarifas.preco_furo)}/furo = "
                f"{format_currency(custo)}"
            )
        if operacao.metodo == metodo_types.RASGO:
            n_comp = int(params.get("n_comp", 0))
            n_larg = int(params.get("n_larg", 0))
            ml = (n_comp * peca["comp"] + n_larg * peca["larg"]) / _D("1000")
            return (
                f"({n_comp} × COMP + {n_larg} × LARG) ÷ 1000 = "
                f"{format_quantity(ml)} ML × {format_quantity(qt)} un × "
                f"{format_currency(tarifas.preco_rasgo_ml)}/ML = "
                f"{format_currency(custo)}"
            )
        faces = params.get("faces", 1)
        return (
            f"{format_quantity(peca['area'])} m² × {faces} face(s) × "
            f"{format_quantity(qt)} un × "
            f"{format_currency(tarifas.preco_m2_face)}/m² = "
            f"{format_currency(custo)}"
        )

    _PARAMS_TEXTO = {
        metodo_types.ESCALAO_AREA: lambda p: "área da peça",
        metodo_types.TEMPO: lambda p: (
            f"setup {format_quantity(normalizar_numero(p.get('setup')) or _D('0'))} min · "
            f"{format_quantity(normalizar_numero(p.get('min_unidade')) or _D('0'))} min/un · "
            f"{p.get('unidades', 1)} un"
        ),
        metodo_types.FURACAO: lambda p: f"{p.get('furos', 0)} furos/un",
        metodo_types.RASGO: lambda p: (
            f"{p.get('n_comp', 0)}× comprimento, {p.get('n_larg', 0)}× largura"
        ),
        metodo_types.REVESTIMENTO: lambda p: f"{p.get('faces', 1)} face(s)",
    }

    def _recalcular(self) -> None:
        peca = self._peca()
        self.area_label.setText(format_quantity(peca["area"]))
        usar_serie_ativo = self.modo_input.currentData() == "SERIE"

        self.ops_table.setRowCount(len(self._operacoes))
        total_std = _D("0")
        total_serie = _D("0")
        tem_custo = False
        for row, operacao in enumerate(self._operacoes):
            custo_std, texto_std = self._custo_operacao(operacao, peca, False)
            custo_serie, texto_serie = self._custo_operacao(operacao, peca, True)
            if custo_std is not None:
                total_std += custo_std
                tem_custo = True
            if custo_serie is not None:
                total_serie += custo_serie
                tem_custo = True
            formula = texto_serie if usar_serie_ativo else texto_std
            valores = (
                f"{operacao.maquina.nome}",
                metodo_types.METODO_CALCULO_LABELS[operacao.metodo].split(" (")[0],
                self._PARAMS_TEXTO[operacao.metodo](operacao.params),
                formula,
                format_currency(custo_std) if custo_std is not None else "—",
                format_currency(custo_serie) if custo_serie is not None else "—",
                "✕ remover",
            )
            for column, valor in enumerate(valores):
                item = QTableWidgetItem(valor)
                if column == len(valores) - 1:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.ops_table.setItem(row, column, item)

        if tem_custo:
            destaque_std = "◀ ativo" if not usar_serie_ativo else ""
            destaque_serie = "◀ ativo" if usar_serie_ativo else ""
            self.totais_label.setText(
                f"Total STD: {format_currency(total_std)} {destaque_std}    |    "
                f"Total SÉRIE: {format_currency(total_serie)} {destaque_serie}"
                f"    (QT {self.qt_input.value()})"
            )
        else:
            self.totais_label.setText(
                "Sem operações — adicione acima ou use um cenário."
            )

    @staticmethod
    def _parse(text: str) -> Decimal | None:
        normalized = (text or "").strip().replace(" ", "").replace(",", ".")
        if not normalized:
            return None
        try:
            return Decimal(normalized)
        except InvalidOperation:
            return None

    @staticmethod
    def _fmt_num(value) -> str:
        numero = normalizar_numero(value)
        if numero is None:
            return ""
        return format(numero.normalize(), "f").replace(".", ",")


class SimuladorCncDialog(QDialog):
    """Modal wrapper of the simulator, openable prefilled from any dialog."""

    def __init__(
        self,
        maquinas: list[MaquinaSimulacao] | None = None,
        parent=None,
        mostrar_cenarios: bool = True,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Simulador de operações CNC / Revestimento")
        self.setModal(True)
        self.setMinimumSize(980, 620)

        if maquinas is None:
            try:
                maquinas = carregar_maquinas_simulacao()
            except Exception:  # noqa: BLE001 - simulator must open even without DB
                maquinas = []

        self.widget = SimuladorCncWidget(
            maquinas, parent=self, mostrar_cenarios=mostrar_cenarios
        )
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText("Fechar")
        buttons.rejected.connect(self.reject)
        buttons.clicked.connect(lambda _button: self.accept())

        layout = QVBoxLayout(self)
        layout.addWidget(self.widget, stretch=1)
        layout.addWidget(buttons)
