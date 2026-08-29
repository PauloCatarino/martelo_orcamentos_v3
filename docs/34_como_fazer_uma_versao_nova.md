# Como fazer uma versão nova do Martelo V3

Escrito para quando o Martelo já está instalado nos PCs dos colegas e é preciso
mexer no programa. Responde a duas perguntas: **onde é que se altera** e
**como é que se garante que o que sai é o que fica instalado**.

---

## Onde alterar: sempre o `main`, sempre a pasta principal

```
C:\Users\Utilizador\Documents\Martelo_Orcamentos_V3
```

É esta a pasta que o VS Code deve ter aberta, e o ramo tem de ser o **`main`**.

O `main` é o que os colegas correm. Tudo o resto — os `claude/...` que aparecem
de vez em quando na lista de ramos — são rascunhos de trabalho que já foram
juntos ao `main` e não servem para gerar instaladores.

**Como confirmar**, sem saber git: em baixo à esquerda no VS Code, na barra
azul, está o nome do ramo. Tem de dizer `main`. Se disser outra coisa, clique aí
e escolha `main` na lista.

O próprio build também avisa. Quando corre o comando de gerar o instalador, a
primeira coisa que aparece é:

```
  ramo: main (44a60c4)
```

Se disser outro ramo, aparece `<-- ATENCAO: os colegas correm o main`.

---

## O caminho, do princípio ao fim

**1. Alterar o programa** no VS Code, na pasta acima, no `main`.

**2. Subir o número da versão.**

```
.venv\Scripts\python.exe scripts\nova_versao.py
```

Sobe o último número (1.0.0 → 1.0.1). É o que se quer quase sempre. Para uma
funcionalidade grande, escreve-se o número à mão:
`scripts\nova_versao.py 1.1.0`.

**3. Correr os testes.**

```
.venv\Scripts\python.exe -m pytest -q
```

**4. Gravar no git e enviar para o GitHub.** É o passo que faz com que o código
deste instalador fique guardado — sem ele, daqui a três meses ninguém consegue
voltar atrás.

**5. Gerar o instalador.**

```
.venv\Scripts\python.exe build_beta.py --producao --installer --profile full
```

Sai `installer\Output\Setup_Martelo_V3_<versão>.exe`.

**6. Instalar em todos os PCs.** Instala-se por cima; não é preciso desinstalar
o que lá está.

---

## Os dois avisos que o build dá

**"já existe um instalador com a versão X"** — parou logo no início, antes de
empacotar seja o que for. Quer dizer que se esqueceu do passo 2. Suba a versão e
repita.

Um número, um instalador. Se saíssem dois ficheiros diferentes com o mesmo
número, deixava de haver maneira de responder a *"ele já tem a correção ou
não?"* — e um dia alguém jura que atualizou quando não atualizou.

(Se o build anterior falhou a meio e é mesmo para repetir o mesmo número,
acrescente `--substituir` ao comando.)

**"N ficheiro(s) por gravar no git"** — o instalador vai ser gerado na mesma,
mas o código que lá vai dentro não fica registado em lado nenhum. Só faz sentido
para uma experiência; para uma versão a sério, faça o passo 4 primeiro.

---

## Saber que versão está num PC

Dentro do Martelo, em cima à direita: **Reportar problema**. A janela que abre
mostra a versão logo na primeira linha.

Serve para quando um colega diz que um problema continua: primeiro confirma-se
que ele tem mesmo a versão onde isso foi corrigido.

O mesmo número fica no diário de bordo desse PC, na primeira linha de cada
arranque:

```
Martelo iniciado (versao=1.0.0, PC=..., SO=...)
```

O diário vive em `C:\Users\<utilizador>\AppData\Local\Martelo Orcamentos V3\`.
