# Menu IMOS IX

Menu da barra lateral (com o logótipo do iX) para as ferramentas do iX CAD no
PC de cada pessoa. Nasceu a 10-10-2026 com uma aba, **Traduções do iX**; as
próximas funcionalidades do iMos entram como abas novas.

Maqueta aprovada pelo Paulo a 10-10-2026 (com o aviso automático; o menu nasce
desligado e o administrador liga-o a quem desenha no iMos).

## Traduções do iX

### O problema

O iX CAD tira os textos de todos os campos de um ficheiro de traduções:
`C:\Program Files\imos AG\iX CAD 2025\BIN\MSG\imos.msg` (UTF-8 com BOM,
34 línguas, ~655 mil linhas `PTG;7134<tab>;Texto`). Alguns campos têm, em
português, nomes que não dizem nada na empresa: o «Kommission» aparece como
«Enc PHC:» porque é aí que se escreve o número da encomenda do PHC.

A lista do que mudar está no Excel `I:\imos_msg.xlsx` (coluna B = referência,
`PTG;10280`; coluna C = texto da empresa) e vai crescendo.

Antes era o `AtualizaIMOSMsgPTG.exe` (fonte em
`Documents\PRODUCAO_LE_V1\PRODUCAO_LE\python atualiza_imos_msg_ptg.py`), com a
lista escrita no código e o caminho do iX **2023** — por isso deixou de servir
no iX 2025. O Martelo V2 já lia o Excel (`app/services/imos_msg_sync.py`, nas
Definições). O V3 junta os dois.

### Como funciona

- O `imos.msg` encontra-se sozinho: iX mais recente pelo registo do Windows
  (`HKLM\SOFTWARE\imos AG\IMOSACT\<versão>\Install`, o mesmo que o Organizer
  usa) e, se falhar, a pasta `iX CAD <ano>` mais recente. Quem o tiver noutro
  sítio escolhe-o em «Procurar…»; a escolha fica nesse PC.
- O Excel é igual para todos (Configurações gerais, chave
  `imos_traducoes_excel`); só o administrador o muda.
- A aba compara as duas coisas: «Já está», «Vai mudar», «Não existe no iX» (o que vai
  mudar fica em cima). As larguras das colunas ajustam-se e ficam guardadas por
  utilizador neste PC.
- **Aplicar traduções**:
  1. se o iX CAD (`imos.exe`) ou o iX Organizer (`Organizer.exe`) estiverem
     abertos, abre a janela «Feche o iX CAD e o iX Organizer», que vê sozinha
     quando fecham; só deixa continuar com os dois fechados;
  2. faz a **cópia**: `imos.msg.copia_AAAA-MM-DD_HHMMSS`, na mesma pasta. Sem
     cópia não se grava nada;
  3. troca só as linhas das referências do Excel — BOM, fins de linha,
     separadores e as outras 34 línguas ficam iguais, byte a byte;
  4. grava num ficheiro temporário e troca (se falhar, o ficheiro fica como
     estava) e confirma no ficheiro gravado que ficou certo;
  5. a janela mostra linha a linha o que mudou (`PTG;1220 «Descrição» →
     «Materiais Usados»`) e o resumo.
- **Repor uma cópia…**: lista as cópias (também as antigas `.bak_` do V2 e
  `.backup_` do executável) e põe a escolhida no lugar. O ficheiro que lá
  estava vai antes para uma cópia `…_antes_de_repor`. Nenhuma cópia é apagada.
- **Aviso ao entrar**: dias úteis, uma vez por dia e por PC, 3 minutos depois
  de abrir o Martelo, se o PC tiver traduções por aplicar (Excel com linhas
  novas, ou iX reinstalado/atualizado). Só pergunta («Abrir IMOS IX» / «Mais
  tarde»); cada pessoa desliga-o na própria aba.

Teste com uma cópia do `imos.msg` de julho (10-10-2026): mudaram exatamente as
4 linhas esperadas (1220, 6128, 10279, 18012) e o resultado ficou igual ao
`imos.msg` atual do PC do Paulo, menos uma alteração feita à mão que não está
no Excel (`PTG;6701` com um espaço no fim).

### Onde está

| O quê | Ficheiro |
|---|---|
| Ler o Excel, comparar, aplicar, cópias, programas abertos | `app/services/imos_traducoes_service.py` |
| Caminhos e aviso ao entrar | `app/ui/helpers/traducoes_imos.py` |
| Página e aba | `app/ui/pages/imos_ix_page.py` |
| Janelas (fechar programas, aplicar, repor) | `app/ui/dialogs/imos_traducoes_dialogs.py` |
| Ícone da barra lateral | `app/ui/assets/icons/imos_ix.png` (do V2, `icon_imos_2025.png`) |
| Acesso | `menu.imos_ix` em `app/services/permission_service.py` (nasce desligado) |
| Testes | `tests/test_imos_traducoes_service.py`, `tests/test_imos_ix_page.py` |

### Cuidados

- Escreve num ficheiro do iX, em `C:\Program Files`. Neste PC a pasta deixa
  «Todos» gravar (vem assim do instalador do iMos); num PC onde não deixe, a
  mensagem diz para pedir permissão de escrita à pasta MSG — sem cópia não se
  grava.
- Uma atualização ou reinstalação do iX volta a pôr o `imos.msg` de fábrica: o
  aviso da manhã apanha isso.
