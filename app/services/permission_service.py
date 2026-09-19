"""Role and per-user permission rules."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User, UserPermission


MENU_PERMISSIONS: OrderedDict[str, str] = OrderedDict(
    (
        ("menu.ajuda", "Ajuda"),
        ("menu.orcamentos", "Orçamentos"),
        ("menu.materias_primas", "Matérias-Primas"),
        ("menu.pesquisa_ia", "Pesquisa IA"),
        ("menu.clientes", "Clientes"),
        ("menu.producao", "Produção"),
        ("menu.encomendas_phc", "Encomendas PHC"),
        ("menu.ponto_situacao", "Ponto de Situação"),
        ("menu.configuracoes", "Configurações técnicas"),
    )
)

# Permissões de AÇÃO, ao contrário das de menu: não escondem um menu, travam
# uma operação concreta. Nascem desligadas — dá-se a quem precisa, em vez de
# tirar a quem não deve.
PERMISSAO_CRIAR_ENCOMENDA_IMOS = "acao.criar_encomenda_imos"
PERMISSAO_PROPAGAR_OPERACOES_VALUESET_OUTROS = (
    "acao.propagar_operacoes_valueset_outros"
)
PERMISSAO_PUBLICAR_MODELO_VALUESET_GLOBAL = "acao.publicar_modelo_valueset_global"
PERMISSAO_ANALISE_LISTA_MATERIAL = "acao.analise_lista_material"
PERMISSAO_CUSTOS_LISTA_MATERIAL = "acao.custos_lista_material"
PERMISSAO_CORRIGIR_LISTA_MATERIAL = "acao.corrigir_lista_material"
PERMISSAO_ASSISTENTE_ORCAMENTOS = "acao.assistente_orcamentos"

ACAO_PERMISSIONS: OrderedDict[str, str] = OrderedDict(
    (
        (PERMISSAO_ANALISE_LISTA_MATERIAL, "Análise da Lista Material — aceder ao módulo"),
        (PERMISSAO_CUSTOS_LISTA_MATERIAL, "Análise da Lista Material — consultar e guardar custos"),
        (PERMISSAO_CORRIGIR_LISTA_MATERIAL, "Análise da Lista Material — aplicar correções"),
        (PERMISSAO_CRIAR_ENCOMENDA_IMOS, "Criar encomendas no iMos"),
        (
            PERMISSAO_PROPAGAR_OPERACOES_VALUESET_OUTROS,
            "Propagar operações ValueSet para modelos globais ou de outros utilizadores",
        ),
        (
            PERMISSAO_PUBLICAR_MODELO_VALUESET_GLOBAL,
            "Publicar e substituir modelos ValueSet globais",
        ),
        (PERMISSAO_ASSISTENTE_ORCAMENTOS, "Assistente dos Orçamentos"),
    )
)

#: Tudo o que o administrador pode marcar na grelha de acessos.
PERMISSOES_EDITAVEIS: OrderedDict[str, str] = OrderedDict(
    list(MENU_PERMISSIONS.items()) + list(ACAO_PERMISSIONS.items())
)

LEGACY_FEATURE_KEYS = (
    "feature_pdf_manager",
    "feature_producao_preparacao",
    "feature_lista_material_audit",
)

DEFAULT_USER_PERMISSIONS = {
    **{key: key != "menu.configuracoes" for key in MENU_PERMISSIONS},
    **{key: False for key in ACAO_PERMISSIONS},
}


@dataclass(frozen=True)
class DescricaoAcesso:
    """O que o administrador lê antes de ligar ou desligar um acesso."""

    grupo: str
    #: Cabeçalho da coluna na grelha (curto: a grelha tem muitas colunas).
    titulo_curto: str
    o_que_faz: str
    para_quem: str


#: Uma entrada por acesso da grelha. Um acesso novo sem descrição faz falhar
#: os testes -- o administrador vem cá poucas vezes e tem de perceber o que
#: está a ligar sem ter de perguntar a ninguém.
DESCRICOES_ACESSOS: OrderedDict[str, DescricaoAcesso] = OrderedDict(
    (
        (
            "menu.ajuda",
            DescricaoAcesso(
                "Menus",
                "Ajuda",
                "Mostra a versão do Martelo instalada no PC e permite instalar a "
                "versão nova que estiver no servidor.",
                "Todos.",
            ),
        ),
        (
            "menu.orcamentos",
            DescricaoAcesso(
                "Menus",
                "Orçamentos",
                "Lista de orçamentos: criar orçamentos e versões, itens e custeio, "
                "mudar o estado, enviar ao cliente por email e exportar PDF/Excel. "
                "Inclui o Dashboard de orçamentos, a Auditoria do custeio e o "
                "Arquivo V2 (orçamentos antigos).",
                "Orçamentação.",
            ),
        ),
        (
            "menu.materias_primas",
            DescricaoAcesso(
                "Menus",
                "Matérias-\nPrimas",
                "Catálogo de matérias-primas do Martelo: inserir, alterar e "
                "descontinuar placas, orlas, ferragens e os respetivos preços. É "
                "daqui que o custeio dos orçamentos tira os preços.",
                "Orçamentação e quem mantém os preços dos fornecedores.",
            ),
        ),
        (
            "menu.pesquisa_ia",
            DescricaoAcesso(
                "Menus",
                "Pesquisa\nIA",
                "Pesquisa inteligente nas matérias-primas do V3, no PHC (ferragens, "
                "madeiras, orlas) e nos catálogos dos fornecedores, com uma "
                "resposta escrita pela IA local. Só consulta, não altera nada.",
                "Orçamentação e Preparação.",
            ),
        ),
        (
            "menu.clientes",
            DescricaoAcesso(
                "Menus",
                "Clientes",
                "Fichas dos clientes (do PHC e temporários). Liga também o aviso "
                "diário (dias úteis, a partir das 09h00) que pergunta se quer "
                "atualizar os clientes novos ou alterados no PHC.",
                "Orçamentação e Administrativa.",
            ),
        ),
        (
            "menu.producao",
            DescricaoAcesso(
                "Menus",
                "Produção",
                "Obras em produção: processos, pastas das obras, Lista "
                "Material/IMOS, CUT-RITE, Centro de Exportação PDF, Ocorrências e "
                "IA Martelo. Liga também o aviso diário (09h00) das obras que o PHC "
                "ou o Streamlit finalizaram ou arquivaram (só as da própria "
                "pessoa).",
                "Preparação (desenhos), Assistente de produção e Produção.",
            ),
        ),
        (
            "menu.encomendas_phc",
            DescricaoAcesso(
                "Menus",
                "Encomendas\nPHC",
                "Consulta das encomendas do PHC e do Cliente Final (Streamlit). Só "
                "leitura.",
                "Quem acompanha encomendas: Produção, Compras, Administrativa.",
            ),
        ),
        (
            "menu.ponto_situacao",
            DescricaoAcesso(
                "Menus",
                "Ponto de\nSituação",
                "Estado das obras em produção fase a fase (Stock, Corte, Orlagem, "
                "CNC, Montagem, Embalagem, Expedição), com indicadores, obras "
                "atrasadas e o botão para sincronizar com o PHC as obras de toda a "
                "gente.",
                "Produção e Direção.",
            ),
        ),
        (
            "menu.configuracoes",
            DescricaoAcesso(
                "Menus",
                "Configurações\ntécnicas",
                "Definições de peças, ValueSet (chaves e modelos), operações e "
                "máquinas, margens padrão, regras de quantidade, biblioteca de "
                "módulos, tarifas do custeio simplificado, caminhos do sistema e "
                "ligação ao iMos. ATENÇÃO: mexe em dados que mudam os orçamentos de "
                "todos. «Utilizadores e Acessos» só aparece ao administrador.",
                "Só os responsáveis técnicos do catálogo.",
            ),
        ),
        (
            PERMISSAO_ANALISE_LISTA_MATERIAL,
            DescricaoAcesso(
                "Lista Material (Produção)",
                "Análise\nLista Material",
                "Abrir o módulo Análise da Lista Material de uma obra: confere os "
                "materiais da LISTAGEM_CUT_RITE com o Woodstore e propõe "
                "referências. Sem este acesso o envio para o CUT-RITE continua a "
                "funcionar.",
                "Preparação (desenhos).",
            ),
        ),
        (
            PERMISSAO_CUSTOS_LISTA_MATERIAL,
            DescricaoAcesso(
                "Lista Material (Produção)",
                "Lista Material\ncustos",
                "Dentro da Análise da Lista Material: ver o separador de custos da "
                "obra, associar matérias-primas do V3, atualizar preços e guardar a "
                "análise de custos. Precisa também do acesso «Análise Lista "
                "Material».",
                "Quem controla custos de obra.",
            ),
        ),
        (
            PERMISSAO_CORRIGIR_LISTA_MATERIAL,
            DescricaoAcesso(
                "Lista Material (Produção)",
                "Lista Material\ncorreções",
                "Dentro da Análise da Lista Material: aplicar as correções (trocar "
                "materiais), importar o custo das ferragens e inserir o relatório "
                "no Excel da obra. ESCREVE no Excel da obra.",
                "Preparação (desenhos) experiente.",
            ),
        ),
        (
            PERMISSAO_CRIAR_ENCOMENDA_IMOS,
            DescricaoAcesso(
                "Produção — iMos",
                "Criar enc.\niMos",
                "Produção → Funções → «Criar Encomenda IMOS…»: cria no iMos a pasta "
                "do cliente (se faltar) e a encomenda da obra. Mostra tudo antes de "
                "gravar, mas ESCREVE na base de dados do iMos.",
                "Preparação (desenhos) que trabalha no iMos.",
            ),
        ),
        (
            PERMISSAO_PROPAGAR_OPERACOES_VALUESET_OUTROS,
            DescricaoAcesso(
                "Catálogo ValueSet",
                "ValueSet\npropagar",
                "Nas chaves e modelos ValueSet: copiar operações para os modelos "
                "GLOBAIS ou de OUTROS utilizadores. Muda o trabalho de outras "
                "pessoas; sem este acesso cada um só mexe nos seus.",
                "Só os responsáveis técnicos do catálogo.",
            ),
        ),
        (
            PERMISSAO_PUBLICAR_MODELO_VALUESET_GLOBAL,
            DescricaoAcesso(
                "Catálogo ValueSet",
                "ValueSet\npublicar global",
                "Publicar um modelo ValueSet como GLOBAL (passa a estar disponível "
                "para todos) ou substituir um global que já existe.",
                "Só os responsáveis técnicos do catálogo.",
            ),
        ),
        (
            PERMISSAO_ASSISTENTE_ORCAMENTOS,
            DescricaoAcesso(
                "Orçamentos — assistente",
                "Assistente\nOrçamentos",
                "Janela do assistente dos Orçamentos, só com os orçamentos da "
                "própria pessoa: resumo diário (dias úteis, a partir das 8h30) dos "
                "enviados há mais de 30 dias sem resposta e dos que estão em «Falta "
                "Orçamentar» há mais de 15 dias, e uma mensagem quando um orçamento "
                "seu passa a Adjudicado ou Não Adjudicado. Nunca envia nada "
                "sozinho. EM PREPARAÇÃO: por agora ainda não aparece nada.",
                "Orçamentação.",
            ),
        ),
    )
)


def nasce_ligado(chave: str) -> bool:
    """Se o acesso vem marcado numa conta nova (antes de o admin mexer)."""
    return bool(DEFAULT_USER_PERMISSIONS.get(chave, False))


def is_admin(user: User | None) -> bool:
    """Return whether the account has full application access."""
    return bool(user is not None and (user.role or "").strip().lower() == "admin")


def permissions_for_user(session: Session, user: User | None) -> dict[str, bool]:
    """Resolve defaults and explicit overrides for one user."""
    if user is None:
        return {key: False for key in PERMISSOES_EDITAVEIS}
    if is_admin(user):
        return {key: True for key in PERMISSOES_EDITAVEIS}

    resolved = dict(DEFAULT_USER_PERMISSIONS)
    rows = session.execute(
        select(UserPermission).where(UserPermission.user_id == user.id)
    ).scalars()
    for row in rows:
        if row.permission_key in PERMISSOES_EDITAVEIS:
            resolved[row.permission_key] = bool(row.enabled)
    return resolved


def pode(permissoes: dict[str, bool] | None, chave: str) -> bool:
    """Leitura defensiva de uma permissão: o que não é dado, não se pode."""
    return bool((permissoes or {}).get(chave, False))


def set_user_permissions(
    session: Session,
    user_id: int,
    permissions: dict[str, bool],
) -> None:
    """Create or update the supplied permission overrides."""
    existing = {
        row.permission_key: row
        for row in session.execute(
            select(UserPermission).where(UserPermission.user_id == user_id)
        ).scalars()
    }
    for key, enabled in permissions.items():
        if key not in PERMISSOES_EDITAVEIS and key not in LEGACY_FEATURE_KEYS:
            continue
        row = existing.get(key)
        if row is None:
            session.add(
                UserPermission(
                    user_id=user_id,
                    permission_key=key,
                    enabled=bool(enabled),
                )
            )
        else:
            row.enabled = bool(enabled)
