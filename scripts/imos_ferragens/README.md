# Ferragens para o iMos: STEP do fabricante → DWG 3D + imagem

Ferramentas para pôr uma ferragem nova na biblioteca do iMos a partir do STEP do
fabricante, sem abrir o CAD: converter, perceber a peça, simplificar, alinhar com a
união, conferir e gerar a imagem da lista de ferragens.

Usadas pela primeira vez no pé SmartFeet (01-10-2026) e nos niveladores LevelUp
(04-10-2026). A lógica repete-se, mas **cada tipo de ferragem pede decisões
próprias** (referencial, o que simplificar, de que lado se fotografa) — ver
[O que muda de ferragem para ferragem](#o-que-muda-de-ferragem-para-ferragem).

## Onde fica cada coisa no iMos

| O quê | Pasta | Campo da União |
|---|---|---|
| DWG 3D (`<NOME>.DWG`) | `I:\Library\ConnDWG` | "Nome do desenho" |
| Imagem 256×256 (`<NOME>.jpg`) | `I:\Library\Info\BITMAPS` | "Preview Image" (lista de ferragens) |

- Mesmo nome base nos dois, escolhido pelo Paulo (ex.: `EMUCA_4030705_NIVELADOR_LEVEL_UP_DIR`).
- DWG em formato 2018 (AC1032), um só sólido na camada 0, milímetros.
- O `I:` é uma pasta de rede **sem Reciclagem**: nada se grava por cima nem se apaga
  (as ferramentas recusam nomes que já existem).
- A configuração da União no iMos é sempre feita pelo Paulo.

## Requisitos

- iX CAD 2025 instalado neste PC (usa o kernel em `C:\Program Files\imos AG\iX CAD 2025\CAD-Kernel`:
  `AcTranslators.exe` e `accoreconsole.exe`). Outra pasta: variável `IXCAD_KERNEL`.
- O Python do `.venv` do Martelo (numpy, scipy, Pillow, matplotlib, PySide6). Os comandos
  Python correm-se **a partir da raiz do repositório**:
  `C:\Users\Utilizador\Documents\Martelo_Orcamentos_V3\.venv\Scripts\python.exe -m scripts.imos_ferragens.<comando>`
  (abaixo abreviado como `python -m ...`).

## Passo a passo

Os exemplos usam uma pasta de trabalho `C:\Temp\ferragem` (qualquer uma serve; os
ficheiros intermédios ficam lá).

### 1. Converter o STEP

```powershell
.\scripts\imos_ferragens\step_para_dwg.ps1 -Step C:\Users\Utilizador\Downloads\40307.step -Pasta C:\Temp\ferragem
```

Dá `40307_limpo.dwg` (sólidos soltos, um por camada), `40307.sat` e
`40307_entidades.txt` (tipo, camada e caixa de cada peça). Uma `SURFACE` na lista é
uma peça que o tradutor não fechou em sólido — não entra numa união; refaz-se com
primitivas no passo 4.

### 2. Perceber a peça

- **Arame**, uma cor por peça:
  ```powershell
  .\scripts\imos_ferragens\arestas.ps1 -Dwg C:\Temp\ferragem\40307_limpo.dwg -Dxf C:\Temp\ferragem\arestas.dxf -Camadas 3,10,16
  python -m scripts.imos_ferragens.arame C:\Temp\ferragem\arestas.dxf --saida C:\Temp\ferragem\arame.png
  ```
- **Medidas exatas** (eixos e raios de cavilhas/furos, faces de apoio, peso):
  ```powershell
  python -m scripts.imos_ferragens.sat corpos C:\Temp\ferragem\40307.sat
  python -m scripts.imos_ferragens.sat faces C:\Temp\ferragem\40307.sat --corpo 3 --tipo cone --eixo y
  python -m scripts.imos_ferragens.sat faces C:\Temp\ferragem\40307.sat --tipo spline
  ```
  As faces `spline` são as que pesam no DWG (5 a 15 kB cada; um plano ou cilindro
  ~0,5 kB). É por elas que se escolhe o que simplificar.
- **Ficha técnica** do fabricante (cotas de montagem):
  `python -m scripts.imos_ferragens.ficha_pdf ficha.pdf --saida C:\Temp\ferragem\ficha`

### 3. Decidir o referencial

- **Se a ferragem substitui o desenho de uma união que já existe**, usar a mesma
  origem e orientação do DWG antigo — assim basta trocar o "Nome do desenho" e os
  pontos de inserção continuam certos. Medir o antigo da mesma maneira (copiar o DWG
  antigo para a pasta de trabalho, `ACISOUT`/`sat faces`, `cortes.ps1`).
- **Se é nova**: origem num ponto de montagem evidente (Z=0 na face do painel onde
  assenta; para pés, centro da placa), unidades mm.

### 4. Montar (o passo que muda sempre)

Um script PowerShell que gera os comandos da consola. Copiar
[`exemplos/nivelador_levelup.ps1`](exemplos/nivelador_levelup.ps1) e trocar as
medidas. A receita habitual:

1. apagar o que não é sólido (SURFACE) e as peças a substituir (`ERASE` com só essa camada visível);
2. `SLICE` / `SUBTRACT` para tirar detalhe pesado (roscas, nervuras, encaixes);
3. primitivas no lugar do que se tirou (`CYLINDER`, `CONE`, `BOX`);
4. `UNION` → um só sólido; `MOVE` + `ROTATE3D` para o referencial;
5. `CHPROP` camada 0 + cor; `-WBLOCK <ficheiro> *` (faz de PURGE).

Simplificar sem perder a forma de fora: o Paulo prefere DWG leves (sem roscas nem
nervuras), mas a peça tem de continuar reconhecível. Pôr `_NON` antes de cada ponto.

### 5. Conferir

```powershell
.\scripts\imos_ferragens\cortes.ps1 -Dwg C:\Temp\ferragem\final.dwg -Dxf C:\Temp\ferragem\cortes.dxf -Passo 0.25
python -m scripts.imos_ferragens.vistas C:\Temp\ferragem\cortes.dxf --saida C:\Temp\ferragem\vistas.png
python -m scripts.imos_ferragens.sobrepor C:\Temp\ferragem\cortes_antigo.dxf C:\Temp\ferragem\cortes.dxf --saida C:\Temp\ferragem\sobreposicao.png --nome-a "antigo" --nome-b "novo"
```

Ver nas vistas se "para cima" e o lado das cavilhas/furos estão certos; na
sobreposição, se os pontos de montagem do novo caem em cima dos do antigo.

### 6. Imagem 256×256

```powershell
.\scripts\imos_ferragens\cortes.ps1 -Dwg C:\Temp\ferragem\final.dwg -Dxf C:\Temp\ferragem\cortes_fino.dxf -Passo 0.15
python -m scripts.imos_ferragens.imagem C:\Temp\ferragem\cortes_fino.dxf --vista=-0.5,-1,-0.45 --saida C:\Temp\ferragem\NOME.jpg --grande C:\Temp\ferragem\conferir.png
```

`--vista` é para onde a câmara olha. Escolher o lado que aparece na foto do
fabricante (é o que ajuda a reconhecer a ferragem na lista). Escrever sempre com
`=` (`--vista=-0.5,...`): sem ele, um valor que começa por "−" é lido como opção. `--cor zincado`
(omissão) ou `--cor aluminio`.

### 7. Pôr na biblioteca

```powershell
.\scripts\imos_ferragens\instalar_na_biblioteca.ps1 -Dwg C:\Temp\ferragem\final.dwg -Imagem C:\Temp\ferragem\NOME.jpg -Nome NOME -Simular
.\scripts\imos_ferragens\instalar_na_biblioteca.ps1 -Dwg C:\Temp\ferragem\final.dwg -Imagem C:\Temp\ferragem\NOME.jpg -Nome NOME
```

Confere nomes livres, formato 2018, 256×256, e o hash depois de copiar.

## O que muda de ferragem para ferragem

| Decisão | Nivelador LevelUp (04-10-2026) | Pé SmartFeet (01-10-2026) |
|---|---|---|
| Referencial | o do desenho antigo da união (`GS_SH_6301`): origem na ponta da cavilha de cima, cavilhas ±X, cima +Z, parede +Y | Z=0 na face do painel, centro da placa em 0,0 |
| Simplificação | peças estampadas reais; cavilhas nervuradas → pinos lisos; excêntricos → cilindros; lingueta (SURFACE) → primitivas | refeito todo com primitivas (a rosca fazia 1 MB) |
| Tamanho | 622 kB / 574 kB (o STEP convertido: 2,8 MB) | 24 kB |
| Cor no DWG | zincado 186,192,200 | alumínio 161,161,160 |
| Imagem | lado da foto da Emuca (cabeça Pozidriv, letra R/L) | 3/4 de cima |
| Esquerdo/direito | dois STEP (espelho), a mesma montagem com medidas espelhadas | — |

Outras ferragens vão trazer outras situações (dobradiças, corrediças, puxadores…):
decidir caso a caso e acrescentar aqui uma linha por tipo.

## Armadilhas da consola OEM (`accoreconsole` do iX CAD 2025)

- **Não existem**: LISP, `PURGE`, `MESHSMOOTH`, `STLOUT`, `PNGOUT`, `SURFSCULPT`,
  `3DOSMODE`, `SECURELOAD`, `TRUSTEDPATHS`. Substitutos: `-WBLOCK <f> *` para limpar;
  os cortes em DXF R12 para ver a peça.
- **`NETLOAD` de uma DLL própria dá "Security error"**: é um bloqueio da imos — não contornar.
- **`OSNAPCOORD` vem a 2**: nos scripts o snap sobrepõe-se às coordenadas escritas
  (aconteceu: 600 cortes saíram todos no mesmo Z). `Get-InicioScript` põe-no a 1 e os
  pontos levam `_NON`.
- **Um comando desconhecido ou uma seleção vazia ("None found") desalinha o resto do
  script** — a consola passa a responder às linhas erradas. Por isso o
  `step_para_dwg.ps1` explode por passagens, contando os blocos antes.
- **`EXPLODE _ALL` desfaz um objeto de cada vez** (o mais antigo primeiro) e
  desfaz sólidos em bocados: congelar as camadas dos sólidos antes.
- **`SAVEAS` para um ficheiro que já existe fica à espera de "Yes"**: usar nomes novos.
- **Uma camada atual não congela**: mudar de camada (`-LAYER _S`) antes de `_F`.
- O STEP pode vir com os eixos trocados (o da Emuca vinha com Z ao contrário).
