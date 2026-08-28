"""O piso da numeracao dos orcamentos, ano a ano.

PORQUE E' QUE ISTO EXISTE
-------------------------
O Martelo V3 entrou ao servico com o ano a meio. Em 2026 os orcamentos
``260001`` a ``260867`` foram feitos no Martelo V2, e as pastas deles estao no
servidor com propostas, PDF e desenhos de clientes reais.

O V3 comeca com a tabela de orcamentos vazia, e a regra normal -- "o proximo e'
o maior ja' usado mais um" -- daria ``260001``. O primeiro orcamento a serio
escrevia dentro da pasta de um cliente antigo, e o segundo dentro da do
seguinte, sem nada avisar.

O piso resolve isso: e' o numero abaixo do qual a numeracao nunca desce, e fica
guardado nas configuracoes, uma chave por ano. Em 2027 o V3 ja' e' dono do ano
inteiro, a chave nao existe, e a numeracao volta a ser a normal.
"""

from __future__ import annotations

#: Grupo em ``system_settings`` onde estas chaves vivem.
GRUPO_NUMERACAO = "Orcamentos"

#: Prefixo das chaves. O ano vai no fim: ``orcamento_numero_minimo_2026``.
PREFIXO_NUMERO_MINIMO = "orcamento_numero_minimo_"


def chave_numero_minimo(ano: int) -> str:
    """Chave, nas configuracoes, do piso da numeracao deste ano."""
    return f"{PREFIXO_NUMERO_MINIMO}{int(ano)}"


def primeiro_numero_do_ano(ano: int) -> int:
    """O numero com que um ano comeca quando nao ha' nada nem piso nenhum."""
    return int(f"{int(ano) % 100:02d}0001")
