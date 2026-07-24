"""Semeia o «Assistente — o meu perfil» com o vocabulário do Word do Paulo.

Transcreve o documento «Ensinar_assistente_Martelo_Paulo_melhorado.docx» para
os quadros do perfil, para servir de exemplo/base. É idempotente: não repete
entradas (tipo + expressão) que já existam.

Uso:
    .venv\\Scripts\\python.exe scripts\\semear_perfil_ia_paulo.py           # user "paulo"
    .venv\\Scripts\\python.exe scripts\\semear_perfil_ia_paulo.py admin     # outro user
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.ia_perfil_service import (  # noqa: E402
    criar_entrada,
    listar_entradas,
)

# (tipo, expressão, significado, campos)
ENTRADAS: list[tuple[str, str, str, str]] = [
    # --- Perguntas que faço (exemplos) ---
    ("pergunta", "Que obras minhas estão atrasadas?",
     "As minhas obras cuja Data Entrega já passou e que ainda não estão Arquivadas.", ""),
    ("pergunta", "Já fizemos algum closet para a J.F. Viva?",
     "Obras desse cliente com «closet» na descrição/notas.", ""),
    ("pergunta", "Obras que estão há muito tempo em Desenho.",
     "Obras ainda em Desenho e que podem estar a demorar a passar para Produção.", ""),
    ("pergunta", "Obras sem preço preenchido.",
     "Avaliar o Preço total e mostrar as obras sem valor.", ""),
    ("pergunta", "Roupeiros de correr com perfis de alumínio.",
     "Obras relacionadas com roupeiros de correr e perfis de alumínio.", ""),
    ("pergunta", "Mostra primeiro os meus resultados e depois os de todos.",
     "Ordem de preferência na apresentação dos resultados.", ""),
    # --- Tipos de trabalho e de móvel ---
    ("movel", "roupeiro", "roupeiros; guarda-fatos", "Descrição produção"),
    ("movel",
     "roupeiro; abrir; correr; curvo; inclinado; módulo; artigo; mesa de cabeceira; "
     "cómoda; cama; estante; módulos superiores; cozinha; colunas; módulos de despensa; "
     "lavandaria; máquinas de secar, lavar ou lavar loiça; quartos; puxadores",
     "termos de móvel/artigo que uso na pesquisa", "Descrição produção"),
    ("movel",
     "Guarnições de compra em «L»; guarnições produzidas; remates; laterais de acabamento; "
     "pilares e vigas",
     "móveis com recortes, vigas, pilares, móveis curvos ou inclinados", "Descrição produção"),
    # --- Materiais e acabamentos ---
    ("material", "lacado", "Obra que leva lacagem, independentemente da cor.",
     "Descrição produção ou Notas"),
    ("material", "lacar; verniz; envernizamento; acabamento; NCS; RAL; cor; velatura",
     "Contém verniz, lacagem, cor RAL ou NCS, pintura ou envernizamento.", ""),
    ("material", "painel produzido; sandwich; HPL",
     "colagem, revestimento, uma face, duas faces, HPL ou termolaminado", ""),
    # --- Estados da obra ---
    ("estado", "está na máquina", "Produção", ""),
    ("estado", "já está fechada", "Arquivado ou Finalizado — indicar qual.", ""),
    ("estado", "a obra já entrou em produção",
     "Pode ainda estar em planeamento ou em Desenho — confirmar o estado.", ""),
    ("estado", "obras em produção",
     "Podem estar suspensas, à espera de material, esquecidas, sem placas/ferragens/orlas, "
     "paradas, com muita montagem, CNC especial, dúvidas de execução ou falta de caderno de encargos.", ""),
    # --- Pessoas ---
    ("pessoa", "o Paulo", "Paulo", ""),
    ("pessoa", "Pedro", "Pedro", ""),
    ("pessoa", "Márcia", "Márcia", ""),
    ("pessoa", "Ana", "Ana", ""),
    ("pessoa", "Elsa", "Elsa", ""),
    ("pessoa", "Cátia", "Cátia", ""),
    ("pessoa", "Andreia", "Andreia", ""),
    ("pessoa", "Bruno", "Bruno", ""),
    ("pessoa", "Ângela", "Ângela", ""),
    ("pessoa", "Dário", "Dário", ""),
    # --- Clientes ---
    ("cliente", "a Viva; a JF; Móveis JF_VIVA; VIVA; JF_VIVA", "MÓVEIS J.F. VIVA", ""),
    # --- Tempo e urgência ---
    ("tempo", "urgente", "entrega nos próximos 2 dias", "Data Entrega"),
    ("tempo", "obra antiga", "começou há mais de 2 meses", "Data Início"),
    # --- Palavras que podem confundir ---
    ("ambigua", "Silva", "«Silva» é o cliente ou o responsável?", ""),
    ("ambigua", "portas", "Refere-se a portas de roupeiro? São de abrir ou de correr?", ""),
    ("ambigua", "corrediças, ferragens, puxadores, acessórios ou iluminação",
     "Que ferragem, componente ou marca pretende procurar?", ""),
    ("ambigua", "móveis com formas geométricas diferentes",
     "Quer procurar móveis especiais ou formas fora do standard?", ""),
    # --- Avisos que me davam jeito ---
    ("aviso", "Orçamentos enviados há mais de 15 dias sem resposta do cliente.",
     "Uma vez por semana, à segunda-feira.", ""),
    ("aviso", "Obras no menu Produção há muito tempo em Desenho.",
     "Notificação uma vez por semana, à segunda-feira.", ""),
    ("aviso", "Obras finalizadas há muito tempo.",
     "Notificar quando o cliente ainda não levantou a obra, para arquivar e faturar.", ""),
    # --- Instruções (exemplos, para o futuro) ---
    ("instrucao_email", "Tom formal e simpático; explicar o estado em linguagem simples.", "", ""),
    ("instrucao_email", "Assinar 'Lança Encanto'; nunca falar de preços.", "", ""),
    ("instrucao_pdf", "Não incluir preços nem notas internas; realçar a Ref. do cliente.", "", ""),
    ("instrucao_texto", "Curto e prático; fases uma por linha; sem descrição de produção.", "", ""),
]


def main() -> int:
    username = sys.argv[1] if len(sys.argv) > 1 else "paulo"
    with SessionLocal() as session:
        user = session.execute(
            select(User).where(User.username == username)
        ).scalars().first()
        if user is None:
            print(f"[ERRO] Utilizador '{username}' não encontrado.")
            return 1

        existentes = {
            (e.tipo, (e.expressao or "").strip())
            for e in listar_entradas(session, user.id)
        }
        criadas = saltadas = 0
        for tipo, expressao, significado, campos in ENTRADAS:
            if (tipo, expressao.strip()) in existentes:
                saltadas += 1
                continue
            criar_entrada(
                session,
                user_id=user.id,
                tipo=tipo,
                expressao=expressao,
                significado=significado,
                campos=campos,
            )
            criadas += 1
        session.commit()

    print(f"Perfil de '{username}': {criadas} entradas criadas, {saltadas} já existiam.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
