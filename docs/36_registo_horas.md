# 36 — Registo de Horas dentro do Martelo

**Pedido do Paulo (02-10-2026):** abandonar a app isolada «Registo de Horas ·
Lança Encanto» (PHP/XAMPP em `C:\xampp\htdocs\Registro_horas`) e pôr o registo
de horas/ponto dentro do Martelo, com menu próprio por utilizador, permissões
por utilizador e os dados na base do Martelo.

## Decisões dele

1. Cada pessoa vê só as suas horas; o administrador vê as de todos.
2. O histórico da app antiga (2025 e 2026) passa para o Martelo. O registo
   oficial começa a **1 de outubro de 2026**.
3. O Pedro já tinha instalado a app isolada (01-10); também passa para o Martelo.
4. Quase só o Paulo (teletrabalho, regista tudo) e o Pedro (híbrido: empresa
   8h–17h e depois horas extra em casa) vão usar — os outros têm o relógio de
   ponto da empresa.
5. Registo flexível: 8h normais por dia, extra depois disso, sábados,
   domingos, feriados e dias de férias.
6. Relatório mensal para `financeiro@lancaencanto.pt`, com horas diárias e
   extra separadas, no **dia 2 de cada mês às 9h20**, com as horas do mês
   anterior — mostrado primeiro, para confirmar ou corrigir.
7. Preço das horas: mais tarde (ainda não há métrica).
8. Lembrete diário quando ficam dias por registar.
9. Pode haver mais alterações depois do teste.

## Regras (iguais às da app antiga — provado com os 322 dias dela)

- **Dia útil:** saída − entrada − pausas (+ 2.º período) + acerto. Até às
  horas normais (8h) são normais; o resto é extra («8 + 3»). Menos de 8h
  desconta ao mês («5 − 3»).
- **Fim de semana, feriado, férias:** tudo extra. **Folga:** desconta («−8»).
- **Cada mês fecha por si.**
- Saída igual ou anterior à entrada = dia seguinte.
- Feriados nacionais calculados (incluindo Sexta-feira Santa e Corpo de Deus).

### O que mudou em relação à app antiga (opiniões aplicadas)

- **2.º período no dia útil** (Entrada/Saída duas vezes, como na folha em
  papel): é o caso do Pedro (8h–17h na empresa + 20h–23h em casa). O «acerto»
  continua para pausas a mais e para o histórico.
- **Extra separadas por tipo de dia** no resumo e na folha (dias úteis,
  sábados, domingos, feriados, férias) — a lei paga-as de forma diferente e é
  por aí que um dia entram os valores em euros.
- As contas de cada dia ficam **gravadas como estavam** quando se guardou:
  mudar as horas normais de alguém não reescreve meses já pagos.
- O email à contabilidade **não leva a cópia geral dos orçamentos**
  (`email_copia`): segue só para a contabilidade e para o próprio.
- O administrador vê as folhas de todos **só para consultar** — as horas são
  declaradas por cada um. O administrador não recebe os avisos.
- Mês já enviado: alterar um dia pede confirmação e lembra que é preciso
  reenviar.

## Onde está

| O quê | Ficheiro |
|---|---|
| Regras (contas, feriados, resumos, agenda) | `app/domain/registo_horas.py` |
| Tabelas `registo_horas_dias`, `registo_horas_envios` | `app/models/registo_horas.py`, migração `20261002_118` |
| Base de dados | `app/services/registo_horas_service.py` |
| Importar a app antiga (só SELECT) | `app/services/registo_horas_importacao.py` |
| Folha em PDF | `app/services/registo_horas_pdf.py` |
| Página | `app/ui/pages/registo_horas_page.py` |
| Diálogos (dia, definições, envio) | `app/ui/dialogs/registo_horas_*.py` |
| Avisos (lembrete diário, envio do dia 2) | `app/ui/helpers/registo_horas_avisos.py` |
| Gerar folha + enviar | `app/ui/helpers/registo_horas_acoes.py` |

- Acesso: `menu.registo_horas` na grelha «Utilizadores e Acessos» — **nasce
  desligado**; o admin liga-o a quem precisa.
- Definições de cada pessoa: `user_prefs` (`registo_horas.config`, JSON).
- Email da contabilidade: `system_settings` → `registo_horas_email_contabilidade`
  (só o admin muda, no botão «Definições…» da página).
- A separação «cada um só vê as suas» é feita pelo Martelo (como nos modelos
  ValueSet); na base de dados as contas normais leem e escrevem todas as
  tabelas de trabalho.

## Estado (04-10-2026)

Testado pelo Paulo na **base real** (VS Code → «Martelo V3 — BASE REAL
(martelo_v3)»): acesso ligado ao paulo e ao Pedro, histórico importado (321
dias da app antiga + 2 registados no Martelo); os 12 meses batem certo com a
app antiga. Cópia da base antiga em
`Documentos\Registo de Horas\copia_app_antiga_horarios_2026-10-04.sql`.
Falta: a versão nova (para o Pedro) e o Paulo desinstalar o XAMPP do PC dele.

**Ao desinstalar o XAMPP:** os serviços do Windows `Apache2.4` e `mysql`
(porta 3307) são do XAMPP; o **`MySQL80`** (porta 3306) é a base de dados do
Martelo de toda a empresa e não se toca.

## Guião de teste (02-10-2026)

A etiqueta castanha no cabeçalho diz em que base se está: pelo VS Code,
«DEVELOPMENT · martelo_v3_dev» ou «BASE REAL · martelo_v3». Fechar e voltar a
abrir o Martelo.

### 1. Dar o acesso
1. Entrar como **admin**.
2. Menu **Configurações** → **Utilizadores e Acessos** → linha do **paulo** →
   coluna **«Registo de Horas»** → marcar → **«Gravar acessos»**.
3. Resultado: o admin já vê no menu da esquerda **«Registo de Horas»** (entre
   «Ocorrências» e «Configurações»).

### 2. Importar o histórico da app antiga
1. Confirmar que o **MySQL do XAMPP** está ligado (XAMPP Control Panel →
   MySQL «Running»).
2. **Sair** e entrar como **paulo** → menu **Registo de Horas**.
3. Botão **«Importar da app antiga…»**.
4. Resultado: pergunta com «A app antiga tem 322 dias registados, de
   01/02/2025 a 01/10/2026 … Vão entrar no Martelo 322 dias (13 meses)» →
   **Sim** → linha de estado «Importados 322 dias…».
5. Na lista **«Últimos meses»** (à direita): set 2026 = **61h**, abr 2026 =
   **48h**, nov 2025 = **105h**, abr 2025 = **87h**.
6. Carregar em **«abr 2025»**: dia 28 = «3 − 5» com «Apagão geral»; o resumo
   dá **Total de horas extra 87h**, feriados 11h.
7. Voltar a carregar em «Importar da app antiga…» → «Todos os dias da app
   antiga já estão no Martelo.»

### 3. Registar um dia
1. Botão **«Este mês»** → duplo clique no dia **2 (sexta)**.
2. Já vem 08:00 → 17:00 com «Descontar almoço». Carregar no botão **«19h»**
   → o resultado muda para **«8 + 2»** («10h trabalhadas · 2h extra»).
3. **Guardar e seguinte** → passa para sábado 3, tipo «Fim de semana».
   Escrever **3** horas → **Guardar**.
4. Resultado na folha: dia 2 «8 + 2», dia 3 «3» com «Sábado»; resumo do mês
   atualizado.

### 4. O caso do Pedro (2.º período)
1. Duplo clique na **terça 6** (a segunda 5 aparece como feriado — 5 de Outubro).
2. Saída **17h**, marcar **«2.º período»**, entrada **20:00**, saída **23:00**.
3. Resultado: **«8 + 3»**. Na folha: «8h – 17h · 20h – 23h».

### 5. Folha em PDF
1. Botão **«Folha em PDF»**.
2. Resultado: abre `Documentos\Registo de Horas\HORAS_PAULO_CATARINO_OUTUBRO_2026.pdf`
   com o logótipo, as colunas Entrada/Saída duas vezes, Normais e Extra
   separadas e o resumo por tipo de dia.

### 6. Definições
1. Botão **«Definições…»** → mudar **Horário habitual** para 08:00 às 19:00 →
   **Guardar**.
2. Duplo clique num dia vazio: já vem com saída 19:00.
3. O campo «Email da contabilidade» está sombreado (só o admin o muda).

### 7. Lembrete dos dias por registar
O lembrete aparece ~1min30s depois de entrar, **uma vez por dia**. Hoje é
provável que já tenha aparecido no passo 2 («Ficou um dia por registar: quinta
01/10», antes de o histórico ser importado) — é esse o aviso.
1. Para o ver outra vez num dia seguinte: deixar um dia útil para trás sem
   registo, fechar o Martelo, entrar como **paulo** e esperar ~1min30s.
2. Resultado: «Ficou um dia por registar: …» com **«Registar agora»** (abre
   esse dia) e **«Mais tarde»**.

### 8. Envio à contabilidade (sem esperar pelo dia 2)
1. Ir a **setembro 2026** (◀) → **«Enviar à contabilidade…»**.
2. Resultado: janela com o resumo, os dias, «Para: financeiro@lancaencanto.pt»
   e a mensagem. **Para testar sem mandar à contabilidade: trocar o «Para»
   pelo seu email.** → «Enviar à contabilidade».
3. Resultado: «As horas de setembro de 2026 seguiram para …»; o email chega
   com o PDF em anexo; no painel: «Enviado à contabilidade a …».
4. Alterar um dia de setembro → pergunta «já foram enviadas … Alterar mesmo
   assim?».

O aviso automático do dia 2 às 9h20 só se vê a 2 de novembro (é o primeiro mês
do registo oficial, outubro).

### 9. Admin vê todos
1. Entrar como **admin** → Registo de Horas.
2. Escolher **«Paulo Catarino»** no **Colaborador** → vê a folha (só
   consulta: «Ver dia», sem «Registar hoje»/«Enviar»).
