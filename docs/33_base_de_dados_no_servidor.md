# Levar a base de dados para o servidor da empresa

Escrito a 28 de agosto de 2026, a pedido do Paulo, enquanto se preparava a
versão 1.0.0.

Hoje a base de dados do Martelo vive no PC do Paulo, que tem de estar sempre
ligado para os colegas trabalharem. O servidor da empresa existe e é o sítio
certo para ela. Este documento diz o que é preciso para a mudança, o que já
está resolvido, e — mais importante — **o que decidir agora para que a mudança
depois seja barata**.

---

## 1. O que há na rede, hoje

Verificado a 28 de agosto de 2026 a partir do PC do Paulo:

| | |
|---|---|
| Rede | grupo de trabalho `WORKGROUP` — **não há domínio Windows** |
| PC do Paulo | `PAULOCATARINO`, `192.168.5.201` |
| Servidor | `SERVER_LE`, `192.168.5.160` |
| MySQL no servidor | **não existe** (porta 3306 fechada) |
| SQL Server no servidor | existe (porta 1433) — é o PHC |
| Partilha de ficheiros | existe (porta 445) — é por onde passam as pastas das obras |

O servidor já corre o SQL Server do PHC. O MySQL do Martelo pode viver ao lado
sem conflito nenhum: são serviços diferentes, em portas diferentes.

---

## 2. Antes disso: o IP do PC do Paulo não é fixo

**Isto é para resolver já, não no futuro.**

O `192.168.5.201` é atribuído pelo router (DHCP), não é fixo. Se o router der
outro endereço àquele PC — depois de um reinício, de uma falha de energia, de
uma mudança de equipamento — **o Martelo deixa de arrancar em todos os PCs ao
mesmo tempo**, e a mensagem que os colegas vêem é só "não foi possível ligar à
base de dados". Ninguém vai adivinhar porquê.

Resolve-se de uma de duas maneiras, ambas de cinco minutos:

- **reserva no router** (preferível): o router passa a dar sempre o mesmo
  endereço àquele PC. Fica registado num sítio só;
- **endereço fixo no PC**: configurar o IP à mão nas propriedades da rede.

Enquanto a base viver no PC do Paulo, isto é obrigatório.

---

## 3. O que já está do lado fácil

Três coisas que não vão dar trabalho na mudança, e vale a pena saber porquê:

**As contas dos colegas não estão presas a máquina nenhuma.** São criadas como
`'nome'@'%'`, ou seja, servem a partir de qualquer PC. Se estivessem ligadas ao
nome de cada computador, mudar de servidor obrigava a recriar tudo à mão.

**A aplicação já não tem o endereço da base no código.** Vem do ficheiro `.env`
que está ao lado do executável, em cada PC. Mudar de servidor é mudar uma linha
— o problema é a linha estar em dez sítios (ver o ponto 5).

**As cópias de segurança já são portáteis.** O `scripts/backup_martelo.py`
recebe a base por argumento e produz exatamente o ficheiro de que a mudança
precisa: com estrutura, dados e procedimentos.

---

## 4. O trabalho da mudança, por ordem

1. **Falar com quem trata do servidor.** Espaço em disco, se pode instalar mais
   um serviço, e — a pergunta que interessa — **se aquele servidor já tem
   cópias de segurança próprias**. Se tiver, a base do Martelo passa a estar
   protegida por elas também, e isso é metade do motivo para a mudar.

2. **Instalar o MySQL 8 no servidor.** Tem de ser 8.0.20 ou mais recente: é a
   partir daí que existe o privilégio `SHOW_ROUTINE`, de que as cópias
   precisam (ver `deploy/mysql_conta_copias.sql`).

3. **Abrir a porta 3306** na firewall do servidor, só para a rede interna.

4. **Copiar a base.** Uma cópia com o script de sempre, restaurada no servidor:

   ```
   .venv\Scripts\python.exe scripts\backup_martelo.py --base martelo_v3
   ```

   O ficheiro que sai leva a estrutura, os dados e os procedimentos.

5. **Recriar as contas — isto não vem na cópia.** É o passo que se esquece. Os
   utilizadores do MySQL e os seus privilégios não vivem dentro da base do
   Martelo; vivem à parte, na base de sistema do MySQL. Uma cópia restaurada
   num servidor novo fica com as tabelas todas e sem ninguém que lhes possa
   tocar. As ferramentas já existem:

   - `deploy/mysql_contas_beta.sql` — cria os perfis e os procedimentos;
   - `scripts/gerar_contas_mysql.py` — gera as contas das pessoas;
   - `CALL martelo_aplicar_grants()` no fim, com a conta root.

6. **Apontar os PCs para o servidor novo** — ver o ponto 5 abaixo.

7. **Mudar as cópias de segurança para o servidor.** A tarefa agendada corre na
   máquina onde a base está. Instalar lá o
   `scripts/instalar_backup_agendado.ps1` e **desligar a do PC do Paulo**, para
   não ficarem duas a copiar a mesma coisa.

8. **Deixar a base antiga quieta durante umas semanas.** Não apagar nada no
   dia da mudança. Se aparecer um problema, é para lá que se volta.

---

## 5. A decisão a tomar antes: como é que os PCs encontram a base

É aqui que se ganha ou perde a mudança futura.

Hoje, cada PC tem o endereço da base escrito no seu ficheiro `.env`. E o
instalador **não substitui um `.env` que já exista** (é de propósito, para não
apagar ajustes locais). Ou seja: no dia em que a base mudar de sítio, alguém
tem de ir a **todos os PCs**, um a um.

Com dez PCs é uma tarde. Uma vez até se aguenta; mas é também a razão por que
estas mudanças se vão adiando.

### Três caminhos

**A. Não fazer nada agora.** No dia da mudança, dar a volta aos PCs. Custa zero
hoje e uma tarde depois. É defensável.

**B. Usar o nome da máquina em vez do IP.** Escrever `PAULOCATARINO` no `.env`
em vez de `192.168.5.201`. Não evita a volta aos PCs, mas protege da mudança de
IP descrita no ponto 2. **Não recomendo para o arranque de 31 de agosto**: num
grupo de trabalho sem domínio, a resolução de nomes é menos fiável que um
endereço, e não é no primeiro dia que se quer descobrir isso. A reserva no
router resolve o mesmo problema melhor.

**C. Pôr o endereço da base num ficheiro no servidor de ficheiros.** A
aplicação lê de lá o servidor e o nome da base, e usa o `.env` só se não
conseguir chegar ao ficheiro. No dia da mudança edita-se **uma linha, num
sítio**, e todos os PCs seguem sozinhos.

Não acrescenta dependência nenhuma: o Martelo já não trabalha sem o
`\\SERVER_LE` — é lá que estão as pastas das obras, os PDF e os projetos. E
resolve mais do que a mudança de servidor: resolve também mudanças de IP,
manutenções e voltar atrás depressa se a mudança correr mal.

Custa meio dia de trabalho, com testes, e **não precisa de ficar pronto para 31
de agosto** — pode entrar em qualquer versão antes da mudança.

### Recomendação

- **Agora, antes do dia 31:** reserva de IP no router (ponto 2). Cinco minutos,
  e evita uma paragem de toda a gente.
- **Antes da mudança para o servidor:** fazer o caminho C. É o que transforma a
  mudança de "uma tarde a dar a volta aos PCs" em "editar uma linha".

---

## 6. O que a mudança resolve, e o que não resolve

**Resolve:** o PC do Paulo deixar de ter de estar ligado para os outros
trabalharem; a base passar a viver numa máquina feita para isso; e, se o
servidor já tiver cópias próprias, mais uma camada de protecção.

**Não resolve:** as cópias de segurança do Martelo continuam a ser precisas. Um
servidor não protege de um apagão a meio de uma escrita, de um `DELETE` errado,
nem de alguém apagar um orçamento sem querer. Um servidor protege do disco de
um PC morrer; as cópias protegem dos enganos — e são coisas diferentes.
