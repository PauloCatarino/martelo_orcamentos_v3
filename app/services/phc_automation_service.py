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

import tempfile
from dataclasses import dataclass
from pathlib import Path

# --- Configuração (afinável sem mexer na lógica) ---------------------------

# Título da janela do PHC a controlar (regex parcial, insensível a maiúsculas).
PHC_WINDOW_TITLE_RE = r".*Dossiers Internos.*"

# Nº de TABs entre campos, contados a partir dos passos manuais do Paulo.
TABS_CLIENTE_ATE_REF = 2
TABS_REF_ATE_DESIGNACAO = 8

# O PHC usa o número de cliente com no mínimo 3 dígitos (ex.: 35 -> 035).
# Números maiores mantêm-se (ex.: 1234 -> 1234).
LARGURA_MIN_NUM_CLIENTE = 3

# Pausas (segundos) para dar tempo ao PHC de responder entre passos.
PAUSA_CURTA = 0.4
PAUSA_APOS_NOVA_PROPOSTA = 1.2
PAUSA_APOS_GRAVAR = 1.5

# Teclas (sintaxe do pywinauto.keyboard.send_keys).
TECLA_NOVA_PROPOSTA = "%n"  # ALT+N
TECLA_GRAVAR_FALLBACK = "%g"  # ALT+G, usado só se não encontrar o botão "Gravar"
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
        PassoTeclas("{ENTER}", "Confirmar cliente"),
        PassoPausa(PAUSA_CURTA),
        _tabs(TABS_CLIENTE_ATE_REF, "Ir até Ref. Cliente"),
    ]

    if ref:
        plano.append(PassoTexto(ref, "Ref. cliente"))
        plano.append(PassoPausa(PAUSA_CURTA))

    plano.append(_tabs(TABS_REF_ATE_DESIGNACAO, "Ir até Designação"))
    plano.append(PassoTexto(designacao, "Linha de designação"))
    plano.append(PassoPausa(PAUSA_CURTA))

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
        window_title_re: str = PHC_WINDOW_TITLE_RE,
        log_path: str | Path | None = None,
    ) -> None:
        self.window_title_re = window_title_re
        self.log_path = Path(
            log_path
            or Path(tempfile.gettempdir()) / "martelo_phc_diagnostico.txt"
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
        self._gravar(janela)
        numero = self._ler_numero_proposta(janela)

        return PhcPropostaResultado(
            numero=numero,
            plano=plano,
            log_path=str(self.log_path),
        )

    def diagnosticar(self) -> str:
        """Despejar a árvore de controlos da janela do PHC para o log.

        Substitui o script de diagnóstico: ajuda a identificar o campo do
        número da proposta para melhorar a leitura automática. Só lê, não
        escreve nada no PHC. Devolve o caminho do ficheiro de log.
        """
        janela = self._conectar_janela()
        with open(self.log_path, "w", encoding="utf-8") as ficheiro:
            try:
                arvore = janela.dump_tree()  # type: ignore[attr-defined]
                ficheiro.write(str(arvore or ""))
            except Exception:  # pragma: no cover - depende do backend/janela
                # Fallback: identificadores de controlos.
                import io
                import contextlib

                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    try:
                        janela.print_control_identifiers()
                    except Exception as exc:  # pragma: no cover
                        buffer.write(f"(sem identificadores: {exc})")
                ficheiro.write(buffer.getvalue())
        return str(self.log_path)

    # -- Passos internos ---------------------------------------------------

    def _conectar_janela(self):
        """Ligar-se à janela 'Dossiers Internos' já aberta do PHC."""
        try:
            from pywinauto import Application
        except ImportError as exc:  # pragma: no cover - dependência instalada
            raise PhcAutomationError(
                "A biblioteca de automação (pywinauto) não está instalada."
            ) from exc

        try:
            app = Application(backend="win32").connect(
                title_re=self.window_title_re, timeout=5
            )
            return app.window(title_re=self.window_title_re)
        except Exception as exc:
            raise PhcAutomationError(
                "Não encontrei a janela 'Dossiers Internos' do PHC aberta.\n\n"
                "Abre o PHC → Dossiers → escolhe 'Proposta' no seletor e "
                "deixa essa janela aberta, depois tenta de novo."
            ) from exc

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
                keyboard.send_keys(passo.keys, pause=0.05)
            elif isinstance(passo, PassoTexto):
                keyboard.send_keys(
                    _escape_literal(passo.texto),
                    with_spaces=True,
                    pause=0.03,
                )

    def _gravar(self, janela) -> None:
        import time

        gravou = False
        try:
            botao = janela.child_window(title=GRAVAR_BOTAO_TITULO)
            botao.click()
            gravou = True
        except Exception:
            gravou = False

        if not gravou:
            from pywinauto import keyboard

            keyboard.send_keys(TECLA_GRAVAR_FALLBACK, pause=0.05)

        time.sleep(PAUSA_APOS_GRAVAR)

    def _ler_numero_proposta(self, janela) -> str | None:
        """Tentar ler o número da proposta atribuído pelo PHC.

        Best-effort: despeja os controlos para o log (para afinarmos depois) e
        devolve ``None`` se não conseguir identificar o número com confiança.
        Nesta fase o número é confirmado pelo utilizador no diálogo.
        """
        try:
            self.diagnosticar()
        except Exception:  # pragma: no cover - diagnóstico é auxiliar
            pass
        return None
