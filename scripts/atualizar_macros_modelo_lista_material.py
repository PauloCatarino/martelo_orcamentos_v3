"""Atualiza um modulo VBA dentro do modelo Lista_Material_IMOS_MARTELO.xltm.

O codigo VBA do modelo vive dentro do ficheiro Excel (vbaProject.bin), por isso
nao pode ser editado como texto. Este script guarda o modulo em `scripts/vba/`
como fonte de verdade e escreve-o no modelo, sempre com copia de seguranca.

Requisitos:
  - Microsoft Excel instalado e pywin32;
  - "Confiar no acesso ao modelo de objeto do projeto VBA" ligado em
    Ficheiro > Opcoes > Centro de Fidedignidade > Definicoes > Definicoes de macro.

Uso:
    python scripts/atualizar_macros_modelo_lista_material.py [caminho_do_xltm]

Sem argumento, usa o modelo do servidor.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

MODELO_SERVIDOR = Path(
    r"\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos"
    r"\Base_Dados_Orcamento\Lista_Material_IMOS_MARTELO.xltm"
)
PASTA_VBA = Path(__file__).resolve().parent / "vba"
#: Os dois módulos do fluxo IMOS. O `RenomeiaListagensImos_13` é o ponto de
#: entrada (macro `ImportarListasFerragensIMOS_14`, a que a app chama) e usa o
#: `Import_List_Ferr_Etiq_11` para as ferragens e a etiqueta.
MODULOS = ("Import_List_Ferr_Etiq_11", "RenomeiaListagensImos_13")


def criar_copia_seguranca(modelo: Path) -> Path:
    carimbo = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = modelo.with_name(f"{modelo.stem}_backup_{carimbo}{modelo.suffix}")
    destino.write_bytes(modelo.read_bytes())
    return destino


def _componente(projeto, nome: str):
    for componente in projeto.VBComponents:
        if componente.Name == nome:
            return componente
    return None


def _projeto_vba(livro):
    try:
        return livro.VBProject
    except Exception as exc:  # pragma: no cover - depende da configuracao do Excel
        raise SystemExit(
            "O Excel nao deixou aceder ao projeto VBA.\n"
            "Ligue 'Confiar no acesso ao modelo de objeto do projeto VBA' "
            f"no Centro de Fidedignidade.\n\nDetalhe: {exc}"
        ) from exc


def _codigo(componente) -> str:
    modulo = componente.CodeModule
    if modulo.CountOfLines == 0:
        return ""
    return str(modulo.Lines(1, modulo.CountOfLines))


def _codigo_do_ficheiro(origem: Path) -> str:
    """Texto do .bas sem as linhas 'Attribute VB_...', que o VBE gere sozinho."""
    linhas = origem.read_text(encoding="cp1252").splitlines()
    uteis = [linha for linha in linhas if not linha.startswith("Attribute VB_")]
    return "\r\n".join(uteis)


def _marcadores(origem: Path) -> tuple[str, ...]:
    """Assinaturas que têm de existir no modelo depois da atualização."""
    texto = origem.read_text(encoding="cp1252")
    return tuple(
        marcador
        for marcador in ("IMOS_IndiceFolhaPorNome", "IMOS_NomeBaseFolha", "idxFerr")
        if marcador in texto
    )


def atualizar_modelo(modelo: Path, modulos: tuple[str, ...] = MODULOS) -> list[str]:
    if not modelo.is_file():
        raise SystemExit(f"Modelo nao encontrado: {modelo}")

    fontes = {}
    for nome in modulos:
        origem = PASTA_VBA / f"{nome}.bas"
        if not origem.is_file():
            raise SystemExit(f"Modulo VBA nao encontrado: {origem}")
        fontes[nome] = origem

    import win32com.client as win32_client

    excel = win32_client.DispatchEx("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False
    try:
        excel.AutomationSecurity = 3  # nao correr macros ao abrir
    except Exception:
        pass

    def abrir():
        # Editable=True e obrigatorio num .xltm: sem isso o Excel cria um livro
        # novo a partir do modelo e o modelo em si nunca chega a ser alterado.
        livro = excel.Workbooks.Open(
            str(modelo), UpdateLinks=0, Editable=True, AddToMru=False
        )
        if livro.ReadOnly:
            raise SystemExit(
                f"O modelo abriu em so-leitura (alguem o tem aberto?):\n{modelo}"
            )
        return livro

    def fechar(livro) -> None:
        if livro is None:
            return
        try:
            livro.Close(False)
        except Exception:
            pass

    trocados: list[str] = []
    livro = None
    try:
        # Substitui-se o TEXTO do modulo em vez de o apagar e importar:
        # o Excel so liberta o nome de um modulo removido depois de fechar o
        # livro, e o Import criaria um "..._1" com o codigo antigo a mandar.
        livro = abrir()
        projeto = _projeto_vba(livro)
        for nome, origem in fontes.items():
            componente = _componente(projeto, nome)
            if componente is None:
                raise SystemExit(
                    f"O modelo nao tem o modulo {nome}. "
                    "Confirme que esta a atualizar o ficheiro certo."
                )
            novo = _codigo_do_ficheiro(origem)
            modulo = componente.CodeModule
            if modulo.CountOfLines:
                modulo.DeleteLines(1, modulo.CountOfLines)
            modulo.AddFromString(novo)
            trocados.append(nome)
        livro.Save()
        fechar(livro)
        livro = None

        # Confirmar no ficheiro gravado, nao so na sessao aberta.
        livro = abrir()
        projeto = _projeto_vba(livro)
        for nome, origem in fontes.items():
            gravado = _codigo(_componente(projeto, nome))
            for marcador in _marcadores(origem):
                if marcador not in gravado:
                    raise SystemExit(
                        f"O codigo novo de {nome} nao ficou gravado no modelo."
                    )
    finally:
        fechar(livro)
        try:
            excel.Quit()
        except Exception:
            pass
    return trocados


def main() -> None:
    modelo = Path(sys.argv[1]) if len(sys.argv) > 1 else MODELO_SERVIDOR
    copia = criar_copia_seguranca(modelo)
    print(f"Copia de seguranca: {copia}")
    trocados = atualizar_modelo(modelo)
    print(f"Modulos atualizados em {modelo}: {', '.join(trocados)}")


if __name__ == "__main__":
    main()
