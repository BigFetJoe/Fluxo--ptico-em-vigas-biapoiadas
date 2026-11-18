# Roadmap

Objetivo final: um aplicativo que **varia automaticamente os parâmetros de processamento**
(principalmente resolução e limiares de detecção de borda) e **plota o erro** das grandezas
modais em relação a uma referência, servindo de base para um artigo de análise de
sensibilidade.

Prioridades atuais: **(1) velocidade**, **(2) mais parâmetros na interface**, (3) design.

Legenda: ✅ feito · 🔜 próximo · ⬜ planejado

---

## Fase 0 — Faxina ✅

- ✅ Repositório só com código; vídeos e resultados fora do git
- ✅ `.gitignore`, `requirements.txt`, teste de fumaça headless funcionando
- ✅ README, ROADMAP, documentação de arquitetura e de rigor metodológico

## Fase 1 — Base para mudar o código com segurança 🔜

Antes de otimizar, é preciso garantir que a otimização **não muda os resultados**.

- ⬜ **Teste de regressão**: rodar o pipeline num vídeo de referência e guardar as saídas
  numéricas (frequência, EVR, forma modal, R²) como "valores de ouro"; cada mudança tem de
  reproduzi-los dentro de uma tolerância.
- ⬜ **Benchmark** (`benchmark.py`): tempo por etapa (leitura, detecção, série, exportação,
  gráficos) num vídeo fixo, para medir o ganho de cada otimização.
- ⬜ **Testes unitários** (pytest) do detector com imagens sintéticas de borda em posição
  sub-pixel conhecida.
- ⬜ **Bugs conhecidos:**
  - ⬜ **B-11 (crítico):** a FFT usa `T = 1/fps` (`structural_modal_analysis.py:70`), mas com
    `taxa_extracao = N` as amostras estão espaçadas de `N/fps`, e o eixo de frequência sai
    errado por um fator N. Com taxa 1 (padrão) está correto.
  - ⬜ **B-12:** `messagebox.showinfo` é chamado de dentro da thread de processamento
    (`tools.py:306`). O Tkinter não é thread-safe e cada vídeo espera um clique em OK.
  - ⬜ **B-13:** erros nos gráficos são só impressos (`tools.py:384`); a GUI informa sucesso
    mesmo sem FFT ou forma modal.

## Fase 2 — Velocidade 🔜

Perfil medido em 2026-11-18 (`1a freq.mp4`, 4565 frames processados de 22822, ROI = frame
inteiro, cProfile, **71 s no total**):

| Etapa | Tempo | % | Causa principal |
|---|---:|---:|---|
| Exportar `dados_vibracao.csv` (formato longo) | 21,4 s | 30 % | ~4,6 M linhas; a coluna `frames_invalidos` repete uma lista como texto em todas as linhas |
| Detecção de borda (`EdgeDetector.detect`) | 20,6 s | 29 % | Laço Python por coluna e por pixel (11 s); Sobel no frame inteiro (5 s) |
| Leitura do vídeo | 6,0 s | 8 % | `read()` decodifica também os frames descartados pela subamostragem |
| Exportar `matriz_deslocamentos.csv` | 5,9 s | 8 % | |
| Gravar `proc_*.jpg` | 5,3 s | 7 % | 1 JPG por frame processado |
| `to_dataframe()` | 4,0 s | 6 % | Recalculado 3× por vídeo; um `merge` + spline por coluna |
| SVD + FFT + gráficos | ~3 s | 4 % | SVD feito 2× |

Otimizações, na ordem de ganho esperado:

- ⬜ **Exportação:** tirar `frames_invalidos` do CSV longo (vai para um resumo por coluna);
  tornar o CSV longo opcional; gravar a matriz em formato binário (`.npz`/Parquet) além do CSV.
- ⬜ **Detector vetorizado:** calcular a máscara de máximos locais acima do limiar na imagem
  inteira com NumPy e pegar a primeira ocorrência por coluna com `argmax`; interpolação
  parabólica vetorizada. Calcular o Sobel só nas colunas usadas (`step`), ou só numa faixa
  em torno da borda do frame anterior.
- ⬜ **Leitura:** `cap.grab()` para frames descartados (não decodifica); `CAP_PROP_POS_FRAMES`
  para pular o corte inicial; recortar a ROI antes do `cvtColor`.
- ⬜ **Visualizações opcionais ou amostradas** (ex.: 1 JPG a cada 100 frames).
- ⬜ **Série temporal em matriz densa:** como as colunas são fixas (`step`), acumular direto
  num array `T × X` com NaN nas falhas; interpolar com NumPy/SciPy de uma vez; calcular
  `to_dataframe()` e a SVD uma única vez.
- ⬜ **Paralelismo:** processar vídeos em processos separados (`multiprocessing`); depois,
  frames em lotes. Essencial para a varredura de parâmetros da Fase 4.

Meta: < 10 s para o mesmo vídeo, com o teste de regressão passando.

## Fase 3 — Parâmetros na interface ⬜

- ⬜ **Expor os parâmetros do detector**, hoje fixos no código: limiar de gradiente, kernel e
  sigma do blur, `ksize` do Sobel, passo entre colunas (`step`), janela e ordem do
  Savitzky-Golay.
- ⬜ **Detector Canny** como opção, com **limiar baixo e limiar alto** (ver
  [rigor metodológico §7](docs/rigor_metodologico.md#7-detector-de-borda-sobel--canny)):
  Canny para localizar a borda + refinamento sub-pixel no gradiente.
- ⬜ **Resolução:** fator de redução da imagem (`cv2.resize`, `INTER_AREA`), com o fator de
  escala mm/px ajustado automaticamente.
- ⬜ Escolha da pasta de saída (hoje fixa em `./frames_saida`).
- ⬜ Salvar e carregar **presets** de parâmetros (JSON).
- ⬜ `metadados.json` por execução: parâmetros, fps e sua fonte, escala, hash do commit,
  versões das bibliotecas, tempo de processamento.
- ⬜ Separar a lógica da GUI: uma CLI (`python -m app_final.cli video.mp4 --params p.json`)
  que a GUI e a varredura reutilizam.

### Design (baixa prioridade)
- ⬜ Layout em abas (Entrada · Detecção · Calibração · Saída), barra de progresso real
  (frames processados / total), preview da detecção de borda ao vivo sobre o 1º frame,
  resumo dos resultados (frequência, EVR, R²/MAC) na própria janela.

## Fase 4 — Análise de sensibilidade automática ⬜ (objetivo final)

- ⬜ **Referência "viga perfeita":**
  - gerador de **vídeo sintético** de viga com deslocamento conhecido (erro absoluto exato);
  - frequência do **acelerômetro** e modelo analítico Euler-Bernoulli para os vídeos reais.
- ⬜ **Métricas de erro:** erro relativo da frequência, **MAC** da forma modal, RMSE do
  deslocamento (sintético), EVR, % de pontos interpolados, tempo de processamento.
- ⬜ **Motor de varredura:** grade fatorial (resolução × limiar baixo × limiar alto) e
  amostragem Latin Hypercube para mais parâmetros; cache de resultados (não reprocessar
  combinações já feitas); execução paralela; tabela consolidada `resultados.csv`.
- ⬜ **Plotagem automática:** erro × parâmetro (com barras de erro entre tomadas), mapas de
  calor de erro para pares de parâmetros, superfície de erro, região ótima destacada.
- ⬜ **Sensibilidade global:** índices de Sobol / Morris (`SALib`) para ranquear a influência
  de cada parâmetro.
- ⬜ Aba "Sensibilidade" na GUI para configurar faixas e disparar a varredura.

## Fase 5 — Artigo ⬜

- ⬜ Script único que regenera todas as figuras e tabelas do artigo.
- ⬜ Fixar versões das dependências e marcar o commit usado (tag `v1.0-artigo`).
- ⬜ Publicar dados (Zenodo, com DOI) e citar código e dados.
- ⬜ Itens de [rigor metodológico](docs/rigor_metodologico.md): janela + interpolação de pico
  na FFT, `L` fixo pelos apoios no ajuste teórico, critério de exclusão de colunas,
  propagação de incerteza da escala, discussão de aliasing e vibração forçada, comparação
  resolução física (distância da câmera) × digital.

## Ideias futuras

- Modos superiores (`find_peaks` no espectro, componentes 2..k da SVD).
- Estimativa de amortecimento (meia potência ou decaimento livre).
- Curvatura modal para localização de dano (sensível a ruído; exige suavização robusta).
- Fluxo óptico denso (Farnebäck) ou correlação de imagem (DIC) como alternativas à detecção
  de borda.
