# Guião de teste — Peça 2: a auditoria passa a ver as chaves ValueSet

Versão de 12-set-2026. **A auditoria nunca escreve nada** — só lê e relata.

---

## Porque é que isto existe

O código de uma chave ValueSet é **texto solto em sete tabelas, sem ligação
nenhuma entre elas**. Se uma chave for renomeada no vocabulário, quem ficou com
o nome antigo não dá um erro: no custeio, a lista de materiais dessa chave vem
**vazia**, o dropdown "Mat. default" fica em branco, e não aparece mensagem nem
fica registo nenhum. Foi assim que o `FERRAGEM_SUPORTE_VARAO` sobreviveu.

A auditoria já vigiava a chave das **peças**. Agora vigia também a dos
**modelos ValueSet** e a das **linhas de módulo**.

---

## 1. Correr a auditoria como está hoje

1. **Configurações → Auditoria ao catálogo** (ou o nome que lá está) →
   **Atualizar**.

**Esperado:** 48 ocorrências — 1 erro, 16 avisos, 31 informações.
Entre os avisos há **um** novo:

> **VALUESET_MODELO_CHAVES_EM_FALTA** — `ROUPEIRO_INOV_POSITIVA`
> *"Faltam 40 chaves que todos os outros modelos do tipo ROUPEIRO têm:
> FERRAGEM_ACESSORIOS_COZINHA, … (e mais 35)."*

2. Selecione essa linha e carregue em **Abrir configuração**.

**Esperado:** salta para **Modelos ValueSet → Roupeiro standard**.

> Este modelo tem 27 chaves; os irmãos têm 67 a 70. Ou está por completar, ou é
> mesmo mais curto de propósito — a auditoria só o põe à frente, quem decide é
> você. A Peça 4 é que vai trazer o "copiar chaves de um modelo para outro".

**Não devem aparecer** `VALUESET_MODELO_CHAVE_INEXISTENTE` nem
`MODULO_CHAVE_VALUESET_INEXISTENTE`: depois de corrigido o SUPORTE_VARAO, a base
está limpa. O ponto seguinte é para confirmar que a rede apanha mesmo.

---

## 2. Provar que a rede funciona (e voltar atrás)

Isto altera dados. Faça só se quiser ver com os seus olhos, e desfaça no fim.

1. **Configurações → Chaves ValueSet**, escolha uma chave pouco usada — por
   exemplo `FERRAGEM_PE_NIVELADOR` — e **anote o código exato**.
2. Edite-a e mude o código para `FERRAGEM_PE_NIVELADOR_X`. Grave.
3. Volte à **Auditoria** e carregue em **Atualizar**.

**Esperado:** aparecem agora ocorrências a **vermelho (ERRO)**, uma por modelo
que usava a chave:

> **VALUESET_MODELO_CHAVE_INEXISTENTE** — `1_ROUP_STD`
> *"A chave FERRAGEM_PE_NIVELADOR não existe no vocabulário (2 linha(s))."*
> Impacto: *"No custeio a lista de materiais desta chave vem vazia, sem erro nem
> registo — a linha fica sem material e ninguém dá por isso."*

Repare que são **duas linhas numa só ocorrência**, e não duas ocorrências.

4. **Abrir configuração** leva ao modelo certo.
5. Vá ao modelo e confirme: essa chave está agora no navegador, no fim, dentro
   do grupo **"Sem grupo"** — é o sinal visual da Peça 1.
6. **Desfaça:** volte às Chaves ValueSet e reponha o código
   `FERRAGEM_PE_NIVELADOR`. Corra a auditoria outra vez: os erros desaparecem.

---

## 3. Chave desativada em vez de renomeada

1. Nas **Chaves ValueSet**, **desative** uma chave que esteja a ser usada.
2. **Auditoria → Atualizar**.

**Esperado:** um **AVISO** (não um erro) por modelo:

> **VALUESET_MODELO_CHAVE_INATIVA** — *"A chave … está inativa no vocabulário
> (N linha(s))."*

3. Reative a chave e confirme que o aviso sai.

---

## 4. O que a auditoria ignora de propósito

Para não encher o relatório de ruído:

- **Linhas desativadas** e **modelos desativados** não são auditados.
- Linhas de módulo **sem chave ValueSet** não geram nada.
- As chaves em falta **não** são comparadas com o vocabulário inteiro — só com
  os **outros modelos do mesmo tipo**. Um roupeiro não é acusado de lhe faltarem
  as chaves de cozinha.
- Um modelo **sozinho no seu tipo** (hoje o `2_LAVANDARIA_STD`, único COZINHA)
  não é comparado com nada.
- Uma chave que só **um** irmão tem não conta como falta — tem de estar em
  **todos** os outros.

> Sem estes cortes, este teste sozinho dava **121 avisos**. Com eles dá **1**.

---

## 5. O que não pode ter mudado

- O total das outras ocorrências mantém-se (as de peças, orlas, operações,
  módulos e regras).
- **Resolver** continua desligado nestas ocorrências novas: são decisões suas,
  não há correção automática. A auditoria diz-lhe que abra a configuração.
