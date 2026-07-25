"""Automação da criação de propostas no PHC CS (janela "Dossiers Internos").

Cria a *proposta base* de um orçamento conduzindo a janela do PHC pelo
teclado — exatamente os passos que o utilizador faz à mão:

    ALT+N  ->  nº de cliente PHC + ENTER  ->  TAB x2  ->  ref. cliente
    ->  TAB x8  ->  linha de designação "Obra: <ref>"  ->  Gravar

**Não** toca na base de dados do PHC — só na interface. O número que o PHC
atribui à proposta é lido de volta (best-effort) para depois ser mapeado no
V3.

A lógica está separada em duas partes:

* ``construir_plano`` / ``construir_designacao`` — puras e testáveis, produzem
  a sequência de passos (teclas/texto/pausas);
* ``PhcAutomationService`` — executa o plano com ``pywinauto`` (só corre no
  Windows, com o PHC aberto).

As constantes de configuração no topo (título da janela, nº de TABs, pausas,
teclas) são fáceis de afinar sem mexer na lógica.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# --- Configuração (afinável sem mexer na lógica) ---------------------------

# A "Dossiers Internos" é uma janela-filha (MDI) DENTRO da janela principal do
# PHC. Por isso ligamo-nos à janela principal ("PHC CS Corporate") e enviamos
# as teclas para o dossier ativo (a proposta que o utilizador tem aberta).
PHC_MAIN_WINDOW_TITLE_RE = r".*PHC CS Corporate.*"
PHC_WINDOW_TITLE_RE = r".*Dossiers Internos.*"

# Nº de TABs entre campos, contados a partir dos passos manuais do Paulo.
TABS_CLIENTE_ATE_REF = 2
TABS_REF_ATE_DESIGNACAO = 8

# O PHC usa o número de cliente com no mínimo 3 dígitos (ex.: 35 -> 035).
# Números maiores mantêm-se (ex.: 1234 -> 1234).
LARGURA_MIN_NUM_CLIENTE = 3

# Pausas (segundos) para dar tempo ao PHC de responder entre passos.
# Deliberadamente lentas: o PHC valida cliente/ref e move o cursor entre
# colunas da grelha, e é preciso dar-lhe tempo para acompanhar.
PAUSA_CURTA = 1.0
PAUSA_APOS_NOVA_PROPOSTA = 2.5
PAUSA_APOS_TABS = 0.8
PAUSA_ANTES_GRAVAR = 1.0
PAUSA_APOS_GRAVAR = 2.5

# Ritmo de escrita: pausa entre teclas (segundos).
RITMO_TECLAS = 0.12
RITMO_TEXTO = 0.08

# Teclas (sintaxe do pywinauto.keyboard.send_keys).
TECLA_NOVA_PROPOSTA = "%n"  # ALT+N
TECLA_GRAVAR = "^g"  # CTRL+G — atalho normal de gravar no PHC
GRAVAR_BOTAO_TITULO = "Gravar"

# Caracteres que o send_keys interpreta como comandos e têm de ser "escapados"
# quando fazem parte de texto literal a escrever num campo.
_CARACTERES_ESPECIAIS = set("^+%~(){}[]")


class PhcAutomationError(RuntimeError):
    """Erro de automação do PHC com mensagem já pronta para o utilizador."""


# --- Passos do plano (puros) ----------------------------------------------


@dataclass(frozen=True)
class PassoTeclas:
    """Enviar uma sequência de teclas (sintaxe send_keys)."""

    keys: str
    descricao: str = ""


@dataclass(frozen=True)
class PassoTexto:
    """Escrever texto literal no campo ativo."""

    texto: str
    descricao: str = ""


@dataclass(frozen=True)
class PassoPausa:
    """Esperar N segundos para o PHC responder."""

    segundos: float
    descricao: str = ""


Passo = PassoTeclas | PassoTexto | PassoPausa


@dataclass(frozen=True)
class PhcPropostaResultado:
    """Resultado de uma tentativa de criar a proposta no PHC."""

    numero: str | None
    plano: list[Passo]
    log_path: str | None = None


def construir_designacao(ref_cliente: str | None) -> str:
    """Linha de designação por omissão: ``Obra: <ref_cliente>``."""
    ref = (ref_cliente or "").strip()
    return f"Obra: {ref}" if ref else "Obra:"


def formatar_num_cliente_phc(num_cliente_phc: str | None) -> str:
    """Formatar o nº de cliente para o PHC (mínimo 3 dígitos: 35 -> 035).

    Números não puramente numéricos são devolvidos tal como estão.
    """
    valor = (num_cliente_phc or "").strip()
    if valor.isdigit():
        return valor.zfill(LARGURA_MIN_NUM_CLIENTE)
    return valor


def _tabs(quantidade: int, descricao: str) -> PassoTeclas:
    """Passo com N TABs (usa a sintaxe ``{TAB N}`` do send_keys)."""
    return PassoTeclas("{TAB " + str(quantidade) + "}", descricao)


def construir_plano(
    *,
    num_cliente_phc: str,
    ref_cliente: str | None,
    designacao: str,
) -> list[Passo]:
    """Construir a sequência de passos para criar a proposta no PHC.

    Reproduz os passos manuais: ALT+N, nº cliente + ENTER, TAB x2, ref.
    cliente, TAB x8, designação. O ``Gravar`` é tratado à parte pelo executor.
    """
    num_cliente = formatar_num_cliente_phc(num_cliente_phc)
    if not num_cliente:
        raise ValueError("Falta o número de cliente PHC.")

    ref = (ref_cliente or "").strip()

    plano: list[Passo] = [
        PassoTeclas(TECLA_NOVA_PROPOSTA, "Nova proposta (ALT+N)"),
        PassoPausa(PAUSA_APOS_NOVA_PROPOSTA, "Esperar abertura da proposta"),
        PassoTexto(num_cliente, "Nº de cliente PHC"),
        PassoPausa(PAUSA_CURTA, "Deixar o PHC validar o nº de cliente"),
        PassoTeclas("{ENTER}", "Confirmar cliente"),
        PassoPausa(PAUSA_CURTA, "Esperar o preenchimento do nome do cliente"),
        _tabs(TABS_CLIENTE_ATE_REF, "Ir até Ref. Cliente"),
        PassoPausa(PAUSA_APOS_TABS),
    ]

    if ref:
        plano.append(PassoTexto(ref, "Ref. cliente"))
        plano.append(PassoPausa(PAUSA_CURTA))

    plano.append(_tabs(TABS_REF_ATE_DESIGNACAO, "Ir até Designação"))
    plano.append(PassoPausa(PAUSA_APOS_TABS, "Esperar a coluna Designação"))
    plano.append(PassoTexto(designacao, "Linha de designação"))
    plano.append(PassoPausa(PAUSA_ANTES_GRAVAR, "Estabilizar antes de gravar"))

    return plano


def _escape_literal(texto: str) -> str:
    """Escapar caracteres especiais do send_keys em texto literal."""
    return "".join(
        "{" + c + "}" if c in _CARACTERES_ESPECIAIS else c for c in texto
    )


def descrever_plano(plano: list[Passo]) -> str:
    """Descrição legível do plano, para confirmação/log."""
    linhas: list[str] = []
    for passo in plano:
        if isinstance(passo, PassoTexto):
            linhas.append(f"  escrever: {passo.texto!r}  ({passo.descricao})")
        elif isinstance(passo, PassoTeclas):
            linhas.append(f"  teclas:   {passo.keys}  ({passo.descricao})")
        else:
            linhas.append(f"  pausa:    {passo.segundos}s")
    return "\n".join(linhas)


# --- Executor (pywinauto — só Windows, com o PHC aberto) -------------------


class PhcAutomationService:
    """Executa o plano de criação de proposta na janela do PHC."""

    def __init__(
        self,
        *,
        main_window_title_re: str = PHC_MAIN_WINDOW_TITLE_RE,
        child_window_title_re: str = PHC_WINDOW_TITLE_RE,
        log_path: str | Path | None = None,
    ) -> None:
        self.main_window_title_re = main_window_title_re
        self.child_window_title_re = child_window_title_re
        self.log_path = Path(
            log_path or Path.home() / "martelo_phc_diagnostico.txt"
        )

    # -- API pública -------------------------------------------------------

    def criar_proposta(
        self,
        *,
        num_cliente_phc: str,
        ref_cliente: str | None,
        designacao: str,
    ) -> PhcPropostaResultado:
        """Criar a proposta base no PHC e devolver o número lido (best-effort)."""
        plano = construir_plano(
            num_cliente_phc=num_cliente_phc,
            ref_cliente=ref_cliente,
            designacao=designacao,
        )

        janela = self._conectar_janela()
        self._focar(janela)
        self._executar_plano(plano)

        # O número da proposta já está visível ANTES de gravar — é o melhor
        # momento para o diagnóstico (a seguir a gravar o ecrã pode limpar).
        antes = self._recolher_diagnostico_seguro(janela, "ANTES DE GRAVAR")

        self._gravar(janela)

        depois = self._recolher_diagnostico_seguro(janela, "DEPOIS DE GRAVAR")
        try:
            self.log_path.write_text(f"{antes}\n\n{depois}\n", encoding="utf-8")
        except OSError:  # pragma: no cover - log é auxiliar
            pass

        return PhcPropostaResultado(
            numero=None,
            plano=plano,
            log_path=str(self.log_path),
        )

    def _recolher_diagnostico_seguro(self, janela, etiqueta: str) -> str:
        """Recolher diagnóstico sem nunca deixar rebentar a automação."""
        cabecalho = f"########## {etiqueta} ##########"
        try:
            return f"{cabecalho}\n{self._recolher_diagnostico(janela)}"
        except Exception as exc:  # pragma: no cover - diagnóstico é auxiliar
            return f"{cabecalho}\n(falhou: {exc})"

    def diagnosticar(self) -> str:
        """Escrever para o log tudo o que se consegue ler da janela do PHC.

        Ajuda a identificar o campo do número da proposta para automatizar a
        leitura. Só lê, não escreve nada no PHC. Devolve o caminho do log.
        """
        janela = self._conectar_janela()
        texto = self._recolher_diagnostico(janela)
        self.log_path.write_text(texto, encoding="utf-8")
        return str(self.log_path)

    def _recolher_diagnostico(self, janela) -> str:
        """Texto de diagnóstico: janelas de topo + controlos e respetivos valores."""
        import contextlib
        import io

        linhas: list[str] = ["=== JANELA LIGADA ==="]
        try:
            linhas.append(f"titulo: {janela.window_text()!r}")
            linhas.append(f"class:  {janela.class_name()!r}")
        except Exception as exc:  # pragma: no cover
            linhas.append(f"(erro a ler a janela: {exc})")

        # Identificadores de controlos: print_control_identifiers escreve para
        # stdout e devolve None, por isso é preciso capturar o stdout.
        linhas.append("\n=== IDENTIFICADORES DE CONTROLOS ===")
        buffer = io.StringIO()
        try:
            with contextlib.redirect_stdout(buffer):
                janela.print_control_identifiers(depth=None)
        except Exception as exc:  # pragma: no cover
            buffer.write(f"(sem identificadores: {exc})\n")
        linhas.append(buffer.getvalue() or "(vazio)")

        # Texto de cada descendente — é aqui que deve aparecer o número (806).
        linhas.append("\n=== TEXTO DOS CONTROLOS (procurar o nº da proposta) ===")
        try:
            for indice, filho in enumerate(janela.descendants()):
                try:
                    valor = (filho.window_text() or "").strip()
                    classe = filho.class_name()
                    auto_id = getattr(filho.element_info, "automation_id", "")
                    ctrl_id = getattr(filho.element_info, "control_id", "")
                except Exception:
                    continue
                if valor:
                    linhas.append(
                        f"[{indice}] class={classe!r} id={ctrl_id!r} "
                        f"auto_id={auto_id!r} texto={valor!r}"
                    )
        except Exception as exc:  # pragma: no cover
            linhas.append(f"(erro a percorrer controlos: {exc})")

        # Janelas de topo, para ajustar os filtros de título se necessário.
        linhas.append("\n=== JANELAS DE TOPO VISÍVEIS ===")
        try:
            from pywinauto import Desktop

            for topo in Desktop(backend="win32").windows():
                try:
                    titulo = topo.window_text()
                except Exception:
                    continue
                if titulo:
                    linhas.append(f"- {titulo!r} ({topo.class_name()!r})")
        except Exception as exc:  # pragma: no cover
            linhas.append(f"(erro a listar janelas: {exc})")

        return "\n".join(linhas)

    # -- Passos internos ---------------------------------------------------

    def _conectar_janela(self):
        """Ligar-se à janela principal do PHC (com a proposta aberta).

        A "Dossiers Internos" é uma janela-filha MDI, por isso controlamos a
        janela principal do PHC e as teclas vão para o dossier ativo.
        """
        try:
            from pywinauto import Application, Desktop
        except ImportError as exc:  # pragma: no cover - dependência instalada
            raise PhcAutomationError(
                "A biblioteca de automação (pywinauto) não está instalada."
            ) from exc

        # 1) Ligar pela janela principal do PHC (caso normal).
        try:
            app = Application(backend="win32").connect(
                title_re=self.main_window_title_re, timeout=5
            )
            return app.window(title_re=self.main_window_title_re)
        except Exception:
            pass

        # 2) Alguns setups expõem a "Dossiers Internos" como janela de topo.
        try:
            app = Application(backend="win32").connect(
                title_re=self.child_window_title_re, timeout=2
            )
            return app.window(title_re=self.child_window_title_re)
        except Exception:
            pass

        # 3) Último recurso: varrer as janelas de topo do ambiente de trabalho.
        try:
            for janela in Desktop(backend="win32").windows():
                try:
                    titulo = janela.window_text()
                except Exception:
                    continue
                if re.search(self.main_window_title_re, titulo) or re.search(
                    self.child_window_title_re, titulo
                ):
                    return janela
        except Exception:
            pass

        raise PhcAutomationError(
            "Não encontrei a janela do PHC aberta.\n\n"
            "Confirma que o PHC (PHC CS Corporate) está aberto, com a janela "
            "Dossiers Internos → 'Proposta' ativa, e tenta de novo."
        )

    def _focar(self, janela) -> None:
        try:
            janela.set_focus()
        except Exception as exc:
            raise PhcAutomationError(
                "Não consegui trazer a janela do PHC para a frente."
            ) from exc

    def _executar_plano(self, plano: list[Passo]) -> None:
        import time

        from pywinauto import keyboard

        for passo in plano:
            if isinstance(passo, PassoPausa):
                time.sleep(passo.segundos)
            elif isinstance(passo, PassoTeclas):
                keyboard.send_keys(passo.keys, pause=RITMO_TECLAS)
            elif isinstance(passo, PassoTexto):
                keyboard.send_keys(
                    _escape_literal(passo.texto),
                    with_spaces=True,
                    pause=RITMO_TEXTO,
                )

    def _gravar(self, janela) -> None:
        """Gravar a proposta com CTRL+G (atalho normal do PHC)."""
        import time

        from pywinauto import keyboard

        keyboard.send_keys(TECLA_GRAVAR, pause=RITMO_TECLAS)
        time.sleep(PAUSA_APOS_GRAVAR)
