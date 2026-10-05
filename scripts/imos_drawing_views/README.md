# Drawing Views do iMos: configuração DV_* e verificador

Ferramentas para pôr o iMos a gerar sozinho plantas e alçados cotados em A3, por obra. O
plano e as decisões estão em [`docs/37_drawing_views_imos.md`](../../docs/37_drawing_views_imos.md).

**Regras deste trabalho** (autorização do Paulo, 05-10-2026):

- Só se escreve na base de testes **`imos_LE_TESTES`**. A `imos_LE` é só leitura.
- Tudo o que se cria tem o prefixo **`DV_`**: nunca se mexe nos princípios que já existiam.
- Nas folhas nunca aparece "Lanca Encanto" nem "LE", porque a LE trabalha para outros
  clientes.
- Em `I:\Library\AttDWG` só entram ficheiros `DV_*` **novos**. O `I:` não tem Reciclagem,
  por isso nada se grava por cima.

## O que cada ficheiro faz

| Ficheiro | Faz |
|---|---|
| `configurar_dv.py` | Escreve na `imos_LE_TESTES` as condições, a cotagem de planta e alçado, as etiquetas, a moldura e o Output batch `DV_Desenhos_Obra`. Por defeito só mostra o SQL. |
| `criar_blocos_etiqueta.ps1` | Cria os blocos de etiqueta `DV_Etq_Modulo(_r)`, `DV_Etq_Nome(_r)` e `DV_Etq_Frente` (com `-Instalar`, copia-os para `I:\Library\AttDWG`). |
| `criar_moldura_a3.ps1` | Cria o DWT da moldura `DV_A3_Obra`: A3 horizontal, só o retângulo exterior e a legenda, centrada na origem, página "Layout 1:1" com o `DV_PlotStyle.ctb`. |
| `estilos_cota_dv.py` | Gera o script da consola que cria o `imosBlocks.dwg` com os estilos de cota `DV_AZUL/VERMELHO/PRETO/VERDE/MAGENTA` (mm de papel, anotativos, texto ISO). Vai para `%APPDATA%\imos AG\iX CAD 2025\config`. |
| `criar_ctb_dv.py` | Cria o `DV_PlotStyle.ctb` (cópia do `iX_PlotStyle.ctb` com a cor 254 das linhas escondidas a cinzento médio e pontilhado). Vai para `I:\Plotters\Plot Styles`. |
| `criar_etiqueta_vista.ps1` + `etiqueta_vista_dxf.py` | Versões novas do círculo de nome das vistas (`imosLabelElevation/Planview.dwg`, pasta `config\DrawingFlags`). |
| `extrair_vistas.ps1` | Copia o DWG de uma obra e extrai cada vista, com as suas cotas e etiquetas, para DXF. |
| `ver_vistas.py` | Desenha essas vistas em PNG, com as cotas na cor do estilo, e lista as cotas por estilo. |
| `dxf2d.py`, `_dv_comum.ps1` | Código comum. |

## Receita

Os comandos Python correm a partir da **pasta principal** do Martelo, por causa do `.env`.

1. Blocos e moldura: `criar_blocos_etiqueta.ps1 -Saida <pasta> -Instalar` e
   `criar_moldura_a3.ps1 -Saida <pasta>`.
2. Base: `python scripts/imos_drawing_views/configurar_dv.py --moldura <pasta>\DV_A3_Obra.dwg --aplicar`
   e depois `--ver` para conferir.
3. No iX Organizer, em Order Manager, escolher a obra e depois Output Batches →
   `DV_Desenhos_Obra`. **O iX CAD tem de estar FECHADO** (o Organizer abre-o, gera e fecha).
4. Conferir: `extrair_vistas.ps1 -Encomenda <obra> -Saida <pasta>` e depois
   `python scripts/imos_drawing_views/ver_vistas.py <pasta>`.

## O que se aprendeu (não se adivinha)

- **Códigos:** os das cotas estão em `iX CAD 2025\BIN\MSG\imos.msg`. Ver o topo do
  `configurar_dv.py`.
- **Molduras:** o DWT fica dentro da base, em `BINDATA` (`INTERNTYPE = 'LAYDWT'`). Os
  `.dwt` de `I:\Library\Bord` são cópias velhas.
- **Etiquetas:** o iMos insere-as **à escala 1, no espaço modelo**. Os blocos vão desenhados
  em mm do modelo para 1:20 (texto de 50 mm) e **não** podem ser anotativos.
- **Escala de anotação:** não mexer na `CANNOSCALE`. A 1:20 as etiquetas anotativas
  aparecem, mas as cotas do iMos (estilos `IMOS_VIEW_*`) ficam 20 vezes maiores.
- **Consola do iX CAD:** não tem `TEXT`, `MTEXT`, `-STYLE` nem `-INSERT`. O texto fixo
  faz-se com atributos constantes. O modo "Constant" do `-ATTDEF` fica memorizado de um
  comando para o seguinte. Para criar e inserir um bloco usa-se `-BLOCK` com o modo
  "Convert".
- **Saída "Drawing views" do Output batch:** `CMSOUTPUTITEM.TYPE = 44`, com um JSON em
  `PARAM_3` (formato no `configurar_dv.py`).
