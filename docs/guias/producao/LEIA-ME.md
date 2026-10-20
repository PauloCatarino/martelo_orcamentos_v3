# Guia do menu Produção

Apresentação para os colegas: como funciona o menu Produção do Martelo V3, com os ecrãs
reais e marcações numeradas. 31 diapositivos.

## O que se entrega

- `Guia_Producao_Martelo_V3.html` — um só ficheiro, com as imagens lá dentro. Abre em
  qualquer PC, sem internet (duplo clique abre no Edge).
  - **Modo leitura** (o que abre): os diapositivos uns por baixo dos outros, para consultar.
  - **▶ Apresentar** (ou tecla `P`): um de cada vez, em ecrã inteiro. `→`/`Espaço` avança,
    `←` recua, `I` índice, `F` ecrã inteiro, `Esc` sai. Um clique na metade direita avança.
  - **⎙ Imprimir / PDF**: um diapositivo por página.
- `Guia_Producao_Martelo_V3.pdf` — o mesmo, em PDF (16:9).

Estes dois ficheiros, as `capturas/` e as `img/` **não vão para o GitHub** (ver
`.gitignore`): têm dados reais de clientes e o repositório é público.

## Como se altera

1. O texto e as marcações estão em `guia_producao.html` (a fonte). Cada marcação é um
   `<span class="box" data-n="3" style="--x:..; --y:..; --bw:..; --bh:..">` com as
   coordenadas em píxeis do recorte do print.
2. Os prints originais estão em `capturas/` (Martelo a 100 %, monitor 2560×1440). Os
   recortes e a zona desfocada (email do cliente) estão em `RECORTES`, no
   `construir_guia.py`.
3. Reconstruir, a partir desta pasta, com o Python do `.venv` da pasta principal:

       python construir_guia.py          # imagens + HTML final
       python construir_guia.py --pdf    # e o PDF (usa o Microsoft Edge)

   Para acertar coordenadas: `python construir_guia.py --grelha form` grava uma imagem
   com uma grelha de 50 px por cima do recorte `form`.

## Como foram tirados os prints

Com o Martelo aberto na base real, só a abrir janelas e menus e a cancelar: nada foi
criado, enviado ou gravado. A captura é feita janela a janela (PrintWindow do Windows),
por isso sai limpa, sem o que estiver por cima no ecrã:

    python ..\capturar_janela.py capturas\22_nova.png            # ecrã inteiro do Martelo
    python ..\capturar_janela.py capturas\22_nova.png --so-topo  # só o diálogo aberto

O mesmo `capturar_janela.py` serve para os guias dos outros menus.
