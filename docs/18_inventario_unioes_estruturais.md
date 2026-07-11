# Inventário das peças estruturais e uniões — passo 1 da generalização

Data: 11 de julho de 2026. Fonte: leitura direta da base de dados
(`def_pecas`, `def_peca_componentes`, `def_peca_operacoes`, `def_regras_quantidade`),
64 peças (61 ativas), cruzada com o catálogo do V2 (prints fornecidos pelo
utilizador) como referência de cobertura.

Objetivo: dar ao utilizador o mapa para decidir, família a família, que
ferragem de união cada peça leva (passo 2 do plano), antes de qualquer
alteração em código ou catálogo.

## 1. Modelo de referência (confirmado no piloto)

- A união pertence à peça que ENCOSTA (a horizontal ou a divisória), nunca à
  lateral que a recebe — evita duplicação de ferragens e CNC (regra
  `CNC_DUPLICADO_PECA_ASSOCIADO` da Auditoria).
- Configuração típica de um associado de união: chave `FERRAGEM_UNIOES`,
  regra `UNIAO_TOPOS_128` (`MAX(2, CEIL(MEDIDA_TOPO / 128))`), zona
  `DOIS_TOPOS`, quantidade `POR_TOPO`, prioridade ValueSet 1 (cavilha
  FER0145) e/ou 2 (parafuso FER0146); CNC na operação da ferragem
  (cavilha→`CNC_ABD`, parafuso→`CNC_VERTICAL`).

## 2. Estado atual das uniões (o que JÁ está configurado)

| Peça | Grupo | Uniões configuradas | Observações |
|---|---|---|---|
| PRATELEIRA FIXA 2000 | PRATELEIRAS FIXAS | cavilha P1 + parafuso P2 | piloto validado |
| DIVISORIA_2000 | LATERAIS | só cavilha P1 | decisão do utilizador no piloto |
| TETO_2000 | TETOS | cavilha P1 + parafuso P2 | |
| FUNDO_0000 | FUNDOS | cavilha P1 + parafuso P2 | |
| FUNDO+PES (conjunto) | FUNDOS | cavilha P1 + parafuso P2 + PES (regra própria) | |

Sem uniões e provavelmente correto assim: PRATELEIRA_AMOVIVEL (leva
SUPORTE_PRATELEIRA por regra própria, zona DOIS_TOPOS), COSTAS (a variante
cozinha COSTA_COM_CNC_0000_PENDURAIS leva NIVELADORES/PENDURAIS), portas e
gavetas (ferragens próprias: dobradiças/corrediças/puxadores).

## 3. Peças estruturais SEM uniões — decisão necessária (passo 2)

Proposta pré-preenchida para o utilizador CONFIRMAR ou CORRIGIR, família a
família. "Igual ao piloto" = cavilha P1 + parafuso P2, `UNIAO_TOPOS_128`,
2 topos, POR_TOPO.

| Família / peça | Situação | Proposta | Decisão do utilizador |
|---|---|---|---|
| FUNDO_2000 | sem uniões (inconsistente com FUNDO_0000) | igual ao piloto | |
| LATERAL_0000/1111/2000/2011/2022/2100/2111/2222 | sem uniões | NENHUMA união própria (recebem a furação via peça que encosta) | |
| TRAVESSA_2200 / TRAVESSA_2222 | sem uniões | igual ao piloto (liga aos 2 topos entre laterais)? | |
| PRUMO_2200 | sem uniões | a definir (prumo liga a quê? topo/fundo?) | |
| TAMPO_2222 (PAINEIS ACABAMENTO) | sem uniões | a definir (aparafusado por baixo? sem união custeada?) | |
| COSTAS (SEM/COM CNC, 0000/0022/2222) | sem uniões de topo | manter sem união (rasgo/agrafada); confirmar se a colocação leva operação | |
| GAVETA (LADO/TRASEIRA/FUNDO/FRENTE) | montagem via MONTAGEM_GERAL no conjunto | manter (a união da caixa é montagem, não UNIAO_TOPOS)? | |

Nota: as LATERAIS ficarem sem união própria é a peça-chave do modelo — se o
utilizador preferir o contrário (união na lateral), o piloto tem de ser
reconfigurado ao contrário para nunca haver dupla contagem.

## 4. Relações topo/lateral (quem encosta a quem)

- Encostam às LATERAIS/DIVISÓRIAS (2 topos, largura da peça = medida do topo):
  TETO, FUNDO, PRATELEIRA FIXA, TRAVESSA.
- DIVISORIA encosta a TETO+FUNDO (2 topos, união própria — já configurada).
- PRATELEIRA AMOVÍVEL pousa em suportes (não é união fixa).
- COSTA cobre o tardoz (rasgo ou sobreposta; pendurais no caso cozinha).
- PORTA/GAVETA ligam por ferragens próprias (dobradiça, corrediça).

## 5. Inconsistências e dados a limpar (achados da leitura)

1. `COSTA_SEM_CNC_2222` tem `funcao = "Selecionar origem…"` — o texto
   placeholder do formulário foi gravado como valor. Corrigir para COSTA e
   avaliar proteção no diálogo (não aceitar o placeholder).
2. Duas formas diferentes de ligar a MESMA ferragem de união: por
   `peca_filha = SISTEMAS_UNIAO` (FUNDO_0000, FUNDO+PES, TETO_2000,
   DIVISORIA_2000) e por `ref = SISTEMAS_UNIAO` sem peça filha
   (PRATELEIRA FIXA 2000). Normalizar para uma única forma na generalização.
3. `TRAVESSA_2222` está com orientação VERTICAL; a TRAVESSA_2200 igual está
   HORIZONTAL. Uniformizar.
4. `GAVETA_CAIXA_MADEIRA` tem transformações `PAI_*` nos filhos;
   `GAVETA_CAIXA_MADEIRA+PUXADOR` não tem nenhuma — os filhos ficam sem
   fórmulas. Completar a segunda (ou recriá-la por "Gravar como" da primeira).
5. Origem estrutural (`funcao`) por preencher nas peças de GAVETAS,
   PRATELEIRAS (fixas e amovíveis) e FRENTE/LADO/TRASEIRA/FUNDO de gaveta.
6. Peças com fórmulas de cabeçalho em falta: TAMPO_2222 e FRENTE_GAVETA e
   afins não têm `formula_comp/larg` (as laterais/tetos/fundos/costas já têm).

## 6. Cobertura vs V2 (referência dos prints; tecnologia nova, lógica nova)

Grupos do V2 ainda sem equivalente no V3 (trabalho de catálogo futuro, não
bloqueia as uniões): REMATES/GUARNICOES (rodateto, rodapé AGL/PVC,
guarnições, painéis de acabamento por face), PORTAS CORRER (painéis + calhas
já existem como SISTEMAS_CORRER), acessórios de ROUPEIROS (porta-calças,
varão trombone, grelha veludo), COZINHAS (balde lixo, tulhas, fundos
alumínio, salva-sifão), SPP/acessórios ajustáveis diversos e SERVICOS
adicionais (CNC 5/15 min, colagem/revestimento M2, embalagem M3 — no V3
existe só OPERACAO_MANUAL genérica).

O V3 tem 61 peças ativas vs ~150 entradas no V2; a estratégia confirmada é
menos peças + variantes por ValueSet/prioridade, pelo que NÃO se pretende
migração 1:1.

## 7. Próximos passos propostos

1. Utilizador preenche a coluna "Decisão" da tabela do ponto 3 (pode ser em
   conversa, família a família).
2. Corrigir as inconsistências do ponto 5 (algumas são configuração manual
   do utilizador; a normalização do ponto 5.2 e a proteção do 5.1 são código).
3. Aplicar as uniões decididas às peças (utilizador na app, com a Auditoria
   do Catálogo a validar: 0 ocorrências `UNIAO_*`/`CNC_DUPLICADO_*`).
4. Só depois: módulo caixote de teste completo (teto+fundo+laterais+
   divisória+prateleiras+costa+porta) e verificação dos consumos por máquina.
