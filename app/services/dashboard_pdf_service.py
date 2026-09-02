"""PDF do dashboard do orçamento: um gráfico por página, A4 deitado.

Os mesmos gráficos que estão no ecrã — o desenho vem todo de
:mod:`app.services.dashboard_desenho`, para o papel e o ecrã nunca contarem
histórias diferentes sobre o mesmo orçamento.

Cada página leva no cabeçalho o número do orçamento, o cliente e a data em que
foi desenhado. Sem isso, uma folha impressa que apareça em cima de uma secretária
daqui a um mês não se sabe de que orçamento é, nem se os custos ainda são estes.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.domain import relatorio_graficos
from app.services import dashboard_desenho
from app.ui import tema

#: A4 deitado, em polegadas.
A4_DEITADO = (11.69, 8.27)

#: Onde fica o cabeçalho, em fração da altura da página.
_Y_CABECALHO = 0.965
_Y_SUBTITULO = 0.930


class MatplotlibIndisponivel(RuntimeError):
    """Não há matplotlib nesta máquina — sem ele não há gráficos nenhuns."""


def _importar_matplotlib():
    try:
        from matplotlib.backends.backend_pdf import PdfPages
        from matplotlib.figure import Figure
    except Exception as erro:  # noqa: BLE001 - import de terceiros
        raise MatplotlibIndisponivel(
            "Não foi possível desenhar os gráficos para PDF.\n\n"
            f"{type(erro).__name__}: {erro}"
        ) from erro
    return PdfPages, Figure


def paginas_do_dashboard(resumo) -> list:
    """Os gráficos a imprimir, um por página, pela ordem do ecrã."""
    from app.ui.widgets.relatorio_dashboards import DashboardsWidget

    paginas = [
        ("barras", grafico)
        for grafico in DashboardsWidget.graficos_de_barras(resumo).values()
    ]
    paginas.append(
        ("pizza", relatorio_graficos.dados_distribuicao(resumo.distribuicao))
    )
    paginas.append(
        ("pizza", relatorio_graficos.dados_distribuicao_blocos(resumo.distribuicao))
    )
    return paginas


def _cabecalho(figura, *, titulo: str, subtitulo: str) -> None:
    figura.text(
        0.5,
        _Y_CABECALHO,
        titulo,
        ha="center",
        va="top",
        fontsize=13,
        fontweight="bold",
        color=tema.CASTANHO_ESCURO,
    )
    figura.text(
        0.5,
        _Y_SUBTITULO,
        subtitulo,
        ha="center",
        va="top",
        fontsize=9,
        color=tema.CASTANHO_MEDIO,
    )


def gerar_pdf_dashboard(
    output_path,
    resumo,
    *,
    titulo: str,
    subtitulo: str = "",
    momento: datetime | None = None,
) -> Path:
    """Escreve o PDF do dashboard e devolve o caminho.

    ``momento`` só existe para os testes poderem fixar a data do rodapé.
    """
    PdfPages, Figure = _importar_matplotlib()
    output_path = Path(output_path)
    agora = momento or datetime.now()
    rodape = f"Custos desenhados em {agora.strftime('%d-%m-%Y %H:%M')}"
    linha_subtitulo = " · ".join(parte for parte in (subtitulo, rodape) if parte)

    with PdfPages(str(output_path)) as pdf:
        for tipo, grafico in paginas_do_dashboard(resumo):
            figura = Figure(figsize=A4_DEITADO, layout="constrained")
            # Espaço no topo para o cabeçalho não se sobrepor ao gráfico.
            figura.get_layout_engine().set(rect=(0.04, 0.03, 0.92, 0.86))
            if tipo == "barras":
                dashboard_desenho.desenhar_barras(figura, grafico)
            else:
                dashboard_desenho.desenhar_pizza(figura, grafico)
            _cabecalho(figura, titulo=titulo, subtitulo=linha_subtitulo)
            pdf.savefig(figura)

    return output_path
