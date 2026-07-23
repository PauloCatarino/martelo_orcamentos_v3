"""Resolve everything that touches the file server, off the UI thread.

Ao selecionar uma obra, o V3 precisava de ir três vezes ao servidor — imagem
IMOS, pasta da obra e pasta do orçamento — e fazia-o na thread da UI: com a
rede lenta, a janela ficava presa a cada clique na lista. Este worker faz esse
trabalho numa thread própria e devolve o resultado já pronto a mostrar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QObject, QSize, Signal, Slot
from PySide6.QtGui import QImage

from app.db.session import SessionLocal
from app.models.producao import Producao
from app.services.imos_imagem_service import resolver_imagem_imos
from app.services.orcamento_pasta_lookup_service import resolver_pasta_orcamento
from app.services.producao_pastas_service import caminho_versao_de_processo
from app.services.producao_service import gerar_nome_enc_imos_ix


#: Resolução máxima usada ao converter a 1ª página de um PDF em imagem.
TAMANHO_RENDER_PDF = QSize(900, 1200)


@dataclass
class DetalheObraResolvido:
    """Everything the detail panel needs, already read from the server."""

    processo_id: int
    pedido_id: int = 0
    pasta_obra: str = ""
    imagem_path: str = ""
    imagem: QImage | None = None
    #: Texto a mostrar quando não há imagem para desenhar.
    imagem_aviso: str = ""
    pasta_orcamento: str = ""
    pasta_servidor: str = ""
    pasta_servidor_existe: bool = False
    erros: list[str] = field(default_factory=list)

    @property
    def tem_imagem(self) -> bool:
        return self.imagem is not None and not self.imagem.isNull()


class DetalheObraWorker(QObject):
    """Live in a worker thread; answer one request per selected process."""

    resolvido = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        #: Escrito pela thread da UI antes de cada pedido. Pedidos mais antigos
        #: do que este são descartados sem ir ao servidor — assim, percorrer a
        #: lista depressa não deixa uma fila de leituras já inúteis.
        self.ultimo_pedido = 0

    @Slot(int, int)
    def resolver(self, pedido_id: int, processo_id: int) -> None:
        """Resolve one process and emit the result (never raises)."""
        if pedido_id < self.ultimo_pedido:
            return

        resultado = DetalheObraResolvido(
            processo_id=processo_id,
            pedido_id=pedido_id,
        )
        try:
            self._resolver(resultado)
        except Exception as erro:  # noqa: BLE001 - reportado, nunca mata a thread
            resultado.erros.append(str(erro))
        self.resolvido.emit(resultado)

    # ---- passos ----------------------------------------------------------
    def _resolver(self, resultado: DetalheObraResolvido) -> None:
        with SessionLocal() as session:
            processo = session.get(Producao, resultado.processo_id)
            if processo is None:
                resultado.imagem_aviso = "Obra já não existe."
                return

            resultado.pasta_servidor = str(processo.pasta_servidor or "").strip()
            resultado.pasta_obra = self._pasta_da_obra(session, processo, resultado)
            resultado.pasta_orcamento = self._pasta_do_orcamento(session, processo)
            caminho_imagem = self._caminho_imagem(session, processo, resultado)

        resultado.pasta_servidor_existe = _e_pasta(resultado.pasta_servidor)

        if caminho_imagem:
            resultado.imagem_path = str(caminho_imagem)
            resultado.imagem, resultado.imagem_aviso = self._carregar_imagem(
                Path(caminho_imagem)
            )
        elif resultado.pasta_servidor_existe:
            # Sem imagem, mas há pasta: a página mostra a árvore de ficheiros.
            resultado.imagem_aviso = ""
        else:
            resultado.imagem_aviso = "Sem imagem IMOS (sem pasta da obra)"

    @staticmethod
    def _pasta_da_obra(session, processo, resultado) -> str:
        try:
            return str(caminho_versao_de_processo(session, processo))
        except Exception as erro:  # noqa: BLE001 - caminho é informativo
            resultado.erros.append(f"pasta da obra: {erro}")
            return str(processo.pasta_servidor or "")

    @staticmethod
    def _pasta_do_orcamento(session, processo) -> str:
        try:
            pasta = resolver_pasta_orcamento(
                session,
                ano=processo.ano,
                num_orcamento=processo.num_orcamento,
                versao_orc=processo.versao_orc,
            )
        except Exception:  # noqa: BLE001 - sem atalho é aceitável
            return ""
        return str(pasta) if pasta is not None else ""

    @staticmethod
    def _caminho_imagem(session, processo, resultado):
        # O nome da encomenda IMOS é derivado, não está guardado na obra.
        nome_enc = gerar_nome_enc_imos_ix(
            processo.ano,
            processo.num_enc_phc,
            processo.versao_obra,
            nome_cliente_simplex=processo.nome_cliente_simplex,
            nome_cliente=processo.nome_cliente,
            ref_cliente=processo.ref_cliente,
        )
        if not nome_enc:
            return None
        try:
            return resolver_imagem_imos(session, nome_enc_imos=nome_enc)
        except Exception as erro:  # noqa: BLE001 - imagem é acessória
            resultado.erros.append(f"imagem IMOS: {erro}")
            return None

    @staticmethod
    def _carregar_imagem(caminho: Path) -> tuple[QImage | None, str]:
        """Read the file into a QImage (safe outside the UI thread)."""
        try:
            if not caminho.is_file():
                return None, "Imagem não encontrada"
        except OSError:
            return None, "Imagem não encontrada"

        if caminho.suffix.lower() == ".pdf":
            imagem = _render_pdf(caminho)
            if imagem is None:
                return None, "PDF — duplo-clique para abrir"
            return imagem, ""

        imagem = QImage(str(caminho))
        if imagem.isNull():
            return None, "Imagem não encontrada"
        return imagem, ""


def _render_pdf(caminho: Path) -> QImage | None:
    try:
        from PySide6.QtPdf import QPdfDocument
    except (ImportError, ModuleNotFoundError):
        return None

    try:
        documento = QPdfDocument()
        documento.load(str(caminho))
        if documento.pageCount() < 1:
            return None
        imagem = documento.render(0, TAMANHO_RENDER_PDF)
        return None if imagem.isNull() else imagem
    except Exception:  # noqa: BLE001 - PDF ilegível não é erro fatal
        return None


def _e_pasta(caminho: str) -> bool:
    if not caminho:
        return False
    try:
        return Path(caminho).is_dir()
    except OSError:
        return False
