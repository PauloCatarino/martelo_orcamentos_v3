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

## 3. Decisões do passo 2 — TOMADAS (12 de julho de 2026)

O utilizador confirmou a regra-chave e configurou ele próprio as uniões na
aplicação (verificado por releitura da base de dados):

| Família / peça | Decisão aplicada |
|---|---|
| LATERAIS (todas) | CONFIRMADO: nenhuma união própria — a união pertence à peça que encosta |
| FUNDO_2000 | igual ao piloto (cavilha P1 + parafuso P2) ✅ configurado |
| TRAVESSA_2200 / TRAVESSA_2222 | igual ao piloto (cavilha P1 + parafuso P2) ✅ configurado |
| PRUMO_2200 | só cavilha P1 ✅ configurado |
| TAMPO_2222 | só cavilha P1 ✅ configurado |
| LADO_GAVETA / TRASEIRA_GAVETA | só cavilha P1 ✅ configurado (uniões da caixa custeadas) |
| COSTAS | reorganizadas: `COSTA_INS_*` (inserida: +RASGO / +MEIA_MADEIRA / +RASGO+PENDURAIS) e `COSTA_ONS_*` (0000/0022/2222); sem união de topo |
| ILUMINACAO | LED → FITA_LED + CALHA_LED (rasgo CNC em curso pelo Codex) |

Todas com `UNIAO_TOPOS_128`, zona DOIS_TOPOS, quantidade POR_TOPO — o modelo
do piloto está generalizado de forma consistente.

## 3b. Auditoria do Catálogo após a configuração (12 de julho, só-leitura)

Resultado: 4 ERROS + 11 avisos + 9 informações. A corrigir pelo utilizador
na aplicação:

1. **CNC duplicado (4 erros)** — a mesma operação CNC está ativa no conjunto
   E no filho/associado (contaria 2×):
   - `COSTA_INS_0000+RASGO+PENDURAIS` × associado NIVELADORES/PENDURAIS
     (CNC_VERTICAL) — desativar numa das origens;
   - `PORTA_SIMPLES+DOBRADICA`, `PORTA_SIMPLES+DOBRADICA+PUXADOR` e
     `PORTA_DUPLA+DOBRADICA+PUXADOR` × filho PORTA_SIMPLES (CNC_MECANIZACAO)
     — desativar a CNC no CONJUNTO (a maquinação pertence à porta simples).
2. **Orlagem sem orla (3 avisos)** — `COSTA_INS_0000+MEIA_MADEIRA`,
   `FUNDO_0000` e `LATERAL_0000` têm ORLAGEM_PECA ativa com código de orlas
   0000 — desativar a operação nessas variantes.
3. **Módulos desatualizados (3 avisos)** — `1_MOD_2_PORTAS`, `MODULO_COZINHA`
   e `PILOTO_CAIXOTE_SIMPLES` guardam o código antigo `COSTA_SEM_CNC_0000`
   (a peça foi renomeada para `COSTA_INS_0000+RASGO`) — substituir os módulos
   a partir de um custeio atualizado quando conveniente.
4. Os avisos `CNC_PECA_E_ASSOCIADO` das portas (dobradiça/puxador) e as
   informações (regras sem uso, substituições ValueSet) são esperados.

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

## 7. Próximos passos (atualizado 12 de julho de 2026)

Estado: passos 1 e 2 concluídos; passo 3 (aplicar uniões) feito pelo
utilizador para as famílias principais. Em aberto:

1. Utilizador corrige na app as ocorrências do ponto 3b (4 erros CNC
   duplicado + 3 avisos de orlagem) e recorre a Auditoria até 0 erros.
2. NOTA DE COORDENAÇÃO: o Codex tem em curso (não commitado, na pasta
   principal) a funcionalidade "rasgos CNC por comprimento geométrico"
   (migrações `20260720_59` e `20260721_60`), a partir da branch
   `codex/pecas-associados`, que NÃO inclui a Fase C já no `main`. Quando o
   Codex commitar, é preciso fazer um merge cuidado das duas linhas (ambas
   tocam no serviço de custeio e no doc 17) ANTES de mais alterações de
   código nesta área.
3. Depois do merge: proteções/normalizações de código pendentes — placeholder
   "Selecionar origem…" rejeitado no diálogo da peça; normalizar a ligação a
   SISTEMAS_UNIAO (peça-filha vs referência); alertas no custeio para uniões
   incompletas (passo 5 do plano) e auditorias adicionais (passo 6).
4. Módulo caixote de teste completo (teto+fundo+laterais+divisória+
   prateleiras+costa+porta) e verificação dos consumos por máquina (passo 7).
5. Completar as fórmulas `PAI_*` na `GAVETA_CAIXA_MADEIRA+PUXADOR` e a
   orientação da `TRAVESSA_2222` (dados, na app).
