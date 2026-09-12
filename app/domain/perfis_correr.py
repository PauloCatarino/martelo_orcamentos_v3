"""Selection of commercial profiles, independent of the costing unit."""
from decimal import Decimal

from app.domain.medidas import normalizar_numero


MODOS = ("AUTO", "COMPRIMENTO", "DESLIGADO")

# O que se compra a` barra, num comprimento comercial fixo: e' so' nestes que
# faz sentido perguntar se a barra chega para a medida necessaria. Os rodizios e
# o amortecedor vendem-se a` unidade e ficam de fora de proposito.
#
# ATENCAO: isto e' uma lista fixa no codigo e as chaves configuram-se na
# aplicacao — uma chave nova de perfil NAO entra aqui sozinha. Para esses casos
# ha' o `selecao_perfil` da definicao de peca ("COMPRIMENTO" forca, "DESLIGADO"
# dispensa); esta lista e' so' o comportamento "AUTO".
CHAVES = {
    "SISTEMA_CORRER_CALHA_SUP", "SISTEMA_CORRER_CALHA_INF",
    "SISTEMA_CORRER_CALHA_U", "SISTEMA_CORRER_CALHA_H",
    "SISTEMA_CORRER_PUXADOR",
}
PECAS = {
    "CALHA_SUP_SISTEMA_CORRER", "CALHA_INF_SISTEMA_CORRER",
    "CALHA_PORTA_CORRER_U", "CALHA_PORTA_CORRER_H",
    "PUXADOR_PORTA_CORRER",
}


def unidade_perfil_und(unidade):
    return (unidade or "").strip().upper() in {"UND", "UN", "UNI", "UNID", "PC", "PCS", "UNIDADE"}


def usa_selecao_comprimento(linha, modo="AUTO"):
    if modo == "DESLIGADO" or getattr(linha, "sem_material", False):
        return False
    if getattr(linha, "tipo_linha", None) not in ("PECA", "FERRAGEM"):
        return False
    return modo == "COMPRIMENTO" or (
        (getattr(linha, "chave_valueset", None) or "").strip().upper() in CHAVES
        or (getattr(linha, "def_peca_codigo", None) or "").strip().upper() in PECAS
    )


def comprimento_positivo(valor):
    numero = normalizar_numero(valor)
    return numero if numero is not None and numero.is_finite() and numero > 0 else None


def ordenar_perfis(opcoes, necessario):
    necessario = comprimento_positivo(necessario)
    if necessario is None:
        return list(opcoes)

    def chave(opcao):
        comp = comprimento_positivo(getattr(opcao, "comp_mp", None))
        if comp is None:
            return (2, Decimal(0))
        return (0, comp - necessario) if comp >= necessario else (1, necessario - comp)

    return sorted(opcoes, key=chave)


def descricao_comprimento(comercial, necessario):
    comp = comprimento_positivo(comercial)
    alvo = comprimento_positivo(necessario)
    if comp is None:
        return "Comprimento comercial desconhecido"
    texto = f"{comp:g} mm"
    if alvo is None:
        return texto + " · medida necessária por definir"
    diferenca = comp - alvo
    if diferenca == 0:
        return texto + " · medida exata"
    return texto + (f" · sobra {diferenca:g} mm" if diferenca > 0 else f" · CURTA: faltam {-diferenca:g} mm")
