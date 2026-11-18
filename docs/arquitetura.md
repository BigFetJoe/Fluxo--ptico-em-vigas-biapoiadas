# Arquitetura

O fluxo de dados é unidirecional e passa por cinco módulos em `app_final/`:

```
main.py ──► tools.ler_vibracoes ──► data_extraction ──► data_visualization ──► structural_modal_analysis
 (GUI)       (laço do vídeo, I/O)     (borda + série)     (gráficos/export)       (SVD, FFT, ajuste)
   ▲
widgets.py (componentes de UI, recebem callbacks — não importam tools)
```

## Módulos

### `main.py`
Entrada Tkinter. Monta os widgets por injeção de dependência (passa callbacks para
`widgets.py`), valida as entradas e roda `tools.ler_vibracoes` para cada vídeo numa
`threading.Thread`, devolvendo progresso e conclusão à UI com `janela.after`.

### `widgets.py`
Fábricas de componentes Tkinter. Duas regiões configuráveis, cada uma com preview (retângulo
vermelho sobre o 1º frame):
- **ROI** — região da viga, recortada antes da detecção de borda;
- **Escala** — região de altura conhecida (mm), usada para o fator mm/px.

### `tools.py`
- `ler_vibracoes` — laço principal: lê frames, aplica corte inicial e subamostragem
  (`taxa_extracao`), recorta a ROI, detecta a borda, acumula em `VibrationTimeSeries`, grava
  imagens de visualização, exporta CSVs e dispara os gráficos.
- `calcular_escala` — mede a altura em px entre a primeira e a última borda da região de
  calibração e devolve `h_mm / altura_px`.
- `smart_imread` / `smart_imwrite` — I/O de imagem seguro para caminhos com acentos (via
  `np.fromfile` / `cv2.imencode`). Use sempre estes em vez de `cv2.imread`/`imwrite`.

### `data_extraction.py`
- `EdgeDetector` — por coluna (passo `step`): Gaussian blur 5×5 → Sobel-Y (ksize 3) → |grad| >
  `grad_threshold` → primeiro máximo local → interpolação parabólica de 3 pontos para o
  deslocamento sub-pixel.
- `VibrationTimeSeries` — acumula pontos por coordenada X (`PointData`), registrando leituras
  válidas e frames inválidos (confiabilidade por coluna). `to_dataframe()` monta a grade
  temporal densa, preenche lacunas (spline cúbica se ≥ 4 pontos, senão linear, depois
  bfill/ffill), subtrai a média temporal de cada coluna e aplica o fator de escala.

### `structural_modal_analysis.py`
- `calcular_frequencia_natural` — SVD da matriz centrada; FFT de `U[:,0]·S[0]`; pico de maior
  magnitude = frequência fundamental. Imprime a razão de variância explicada (EVR) do 1º
  componente.
- `extrair_forma_modal` — `Vt[0,:]` escalado, com o sinal corrigido (ambiguidade da SVD) pela
  correlação com os dados.
- `suavizar_forma_modal` — Savitzky-Golay (janela 51, ordem 3).
- `ajustar_curva_teorica` — mínimos quadrados de `A·sin(πx/L+φ)+C`, com R².

### `data_visualization.py`
Gera `integridade_dados.html`, `frequencia_natural_FFT.html`, `forma_modal.html` e
`forma_modal_deslocamento_max.xlsx`. É aqui que as funções de análise modal são chamadas.

## Convenções

- Coordenadas de ROI/escala em **porcentagem** (0–100) do frame, esquema `x1/x2/y1/y2`; a
  escala acrescenta `h_mm`.
- Saída em `./frames_saida/<nome_do_vídeo>/`, relativa ao diretório de trabalho; a pasta é
  apagada no início de cada execução.
- CSVs em padrão brasileiro: `sep=';'`, `decimal=','`.
- Comentários, docstrings e textos de UI em português.
