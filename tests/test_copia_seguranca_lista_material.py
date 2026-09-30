"""Cópias de segurança da Lista Material (obra 1637, 30-09-2026).

O Excel recusa caminhos acima de 255 caracteres e o nome antigo da cópia
repetia a lista inteira: na 26.1637_01_01_LINHAS_DIREITAS dava 256 e tanto a
importação do custo das ferragens como o relatório de custos falhavam com
«Não foi possível executar o método SaveCopyAs da classe Workbook».
"""
from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest
from openpyxl import Workbook

from app.services import analise_lista_material_service as svc
from app.services.lista_material_excel_com import descrever_erro

ERRO_EXCEL_1637 = Exception(
    -2147352567, 'Ocorreu uma exceção.',
    (0, 'Microsoft Excel', 'Não foi possível executar o método SaveCopyAs da classe Workbook',
     'xlmain11.chm', 0, -2146827284), None)


def _obra(tmp_path, comprimento_copias):
    """Pasta de obra cuja pasta Copias fica com o comprimento pedido."""
    base = tmp_path.resolve()  # o serviço mede o caminho resolvido (sem nomes 8.3)
    resto = comprimento_copias - (len(str(base / 'x' / 'Analise_Lista_Material' / 'Copias')) - 1)
    pasta = base / ('o' * resto)
    pasta.mkdir()
    assert len(str(pasta / 'Analise_Lista_Material' / 'Copias')) == comprimento_copias
    return pasta


def _livro(pasta, nome='Lista_Material_1637_01_26_LINHAS_DIREITAS.xlsm', conteudo=b'livro'):
    path = pasta / nome
    path.write_bytes(conteudo)
    return path.resolve()


def test_copia_da_1637_cabe_no_limite_do_excel_e_diz_de_que_lista_e(tmp_path):
    # Na 1637 a pasta Copias tem 180 caracteres: o nome antigo dava 256.
    path = _livro(_obra(tmp_path, 180))
    copia = svc.backup_path(path, 'antes_ferragens')
    assert len(str(copia)) <= svc.LIMITE_CAMINHO_EXCEL
    assert copia.parent == path.parent / 'Analise_Lista_Material' / 'Copias'
    assert copia.name.startswith('1637_01_26_LINHAS_DIREITAS_antes_ferragens_')
    assert 'Lista_Material_' not in copia.name
    assert copia.suffix == '.xlsm'


def test_nome_da_lista_so_se_corta_quando_nao_cabe(tmp_path):
    path = _livro(_obra(tmp_path, 200))
    copia = svc.backup_path(path, 'antes_relatorio')
    assert len(str(copia)) <= svc.LIMITE_CAMINHO_EXCEL
    assert copia.name.startswith('1637_01_26_')
    assert '_antes_relatorio_' in copia.name
    # Pasta tão comprida que não sobra lugar para o nome da lista.
    longa = _livro(_obra(tmp_path, 215))
    assert svc.backup_path(longa, 'antes_relatorio').name.startswith('antes_relatorio_')


def test_copia_pelo_windows_igual_ao_disco_e_nunca_por_cima(tmp_path):
    path = _livro(tmp_path, conteudo=b'estado antes')
    primeira = svc.copia_de_seguranca(path, 'antes_analise', svc.fingerprint(path))
    segunda = svc.copia_de_seguranca(path, 'antes_analise')
    assert primeira != segunda
    assert primeira.read_bytes() == segunda.read_bytes() == b'estado antes'


def test_copia_diferente_da_analise_nao_deixa_continuar(tmp_path):
    path = _livro(tmp_path)
    with pytest.raises(ValueError, match='mudou'):
        svc.copia_de_seguranca(path, 'antes_relatorio', 'hash-da-analise')


def test_caminho_comprido_demais_dito_em_portugues(tmp_path, monkeypatch):
    path = _livro(tmp_path)
    longe = tmp_path / 'nao_existe' / ('x' * 260 + '.xlsm')
    monkeypatch.setattr(svc, 'backup_path', lambda *_: longe)
    with pytest.raises(ValueError, match='demasiado comprido') as erro:
        svc.copia_de_seguranca(path, 'antes_relatorio')
    assert 'nada foi alterado' in str(erro.value)
    assert 'caracteres' in str(erro.value)


def test_outra_falha_da_copia_dita_em_portugues(tmp_path, monkeypatch):
    path = _livro(tmp_path)
    monkeypatch.setattr(svc, 'backup_path', lambda *_: tmp_path / 'nao_existe' / 'c.xlsm')
    with pytest.raises(ValueError, match='Não foi possível gravar a cópia de segurança'):
        svc.copia_de_seguranca(path, 'antes_ferragens')


def test_erro_do_excel_legivel():
    assert descrever_erro(ERRO_EXCEL_1637) == (
        'Microsoft Excel: Não foi possível executar o método SaveCopyAs da classe Workbook')
    assert descrever_erro(ValueError('Feche o Excel.')) == 'Feche o Excel.'


def test_nenhuma_copia_pede_ao_excel():
    assert '.SaveCopyAs(' not in inspect.getsource(svc)


# --- Excel a fingir: as cópias têm de existir antes de o livro ser gravado. ---

class _Folha:
    def __init__(self, livro, nome):
        self.livro, self.Name = livro, nome

    @property
    def Index(self):
        return self.livro.folhas.index(self) + 1

    def Calculate(self):
        pass

    def Copy(self, After=None, Before=None):
        destino = (After or Before).livro
        posicao = destino.folhas.index(After) + 1 if After else destino.folhas.index(Before)
        destino.folhas.insert(posicao, _Folha(destino, self.Name))


class _Folhas:
    def __init__(self, livro):
        self.livro = livro

    @property
    def Count(self):
        return len(self.livro.folhas)

    def Item(self, i):
        return self.livro.folhas[i - 1]

    def Add(self, After=None):
        folha = _Folha(self.livro, 'Nova')
        self.livro.folhas.insert(self.livro.folhas.index(After) + 1, folha)
        return folha

    def __iter__(self):
        return iter(list(self.livro.folhas))


class _Livro:
    ReadOnly = False

    def __init__(self, path, gravacoes):
        self.path, self.gravacoes = Path(path), gravacoes
        self.folhas = [_Folha(self, 'LISTAGEM_CUT_RITE')]
        self.Worksheets = _Folhas(self)

    def SaveCopyAs(self, *_):
        raise AssertionError('A cópia de segurança já não passa pelo Excel.')

    def Save(self):
        copias = self.path.parent / 'Analise_Lista_Material' / 'Copias'
        self.gravacoes.append(sorted(p.name for p in copias.iterdir()))

    def Close(self, _guardar):
        pass


def _excel_a_fingir(monkeypatch):
    gravacoes = []
    excel = SimpleNamespace(Quit=lambda: None, CalculateFull=lambda: None)
    excel.Workbooks = SimpleNamespace(Open=lambda p, **_: _Livro(p, gravacoes))
    win32 = SimpleNamespace(DispatchEx=lambda _nome: excel)
    monkeypatch.setattr(svc, 'importlib', SimpleNamespace(import_module=lambda _nome: win32))
    return gravacoes


def test_relatorio_de_custos_numa_obra_como_a_1637(tmp_path, monkeypatch):
    gravacoes = _excel_a_fingir(monkeypatch)
    monkeypatch.setattr(svc, '_escrever_relatorio_custo', lambda *_a, **_k: None)
    path = _livro(_obra(tmp_path, 180))
    nome = svc.export_cost_report(path, svc.fingerprint(path), '1637_01_26_LINHAS_DIREITAS', [], {}, [])
    assert nome.startswith('Custo_V3_')
    [copias] = gravacoes
    assert len(copias) == 1 and '_antes_relatorio_' in copias[0]
    assert (path.parent / 'Analise_Lista_Material' / 'Copias' / copias[0]).read_bytes() == b'livro'


def test_custo_das_ferragens_numa_obra_como_a_1637(tmp_path, monkeypatch):
    gravacoes = _excel_a_fingir(monkeypatch)
    pasta = _obra(tmp_path, 180)
    lista = Workbook()
    lista.active.title = 'LISTAGEM_CUT_RITE'
    path = pasta / 'Lista_Material_1637_01_26_LINHAS_DIREITAS.xlsx'
    lista.save(path)
    custo = Workbook()
    custo.active.append(('Nome iMos (Nome Uniao)', 'Ref PHC', 'Qt', 'Un'))
    custo.active.append(('CAVILHA', 'FF00001', 30, 'un'))
    fonte = pasta / svc.HARDWARE_FILENAME
    custo.save(fonte)
    assert svc.import_hardware_cost(path, fonte) == fonte.resolve()
    [copias] = gravacoes
    assert len(copias) == 1 and '_antes_ferragens_' in copias[0]
