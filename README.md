# Fluxo óptico em vigas biapoiadas

**Monitoramento de integridade estrutural (SHM) de vigas por visão computacional.**

Aplicativo de pesquisa que extrai a vibração de uma viga biapoiada a partir de vídeo de alta
velocidade e estima seus parâmetros modais — **frequência natural** e **forma modal** — sem
sensores de contato. Os resultados são validados contra acelerômetros.

O projeto é a base de um artigo de **análise de sensibilidade**: como os parâmetros de
processamento (resolução, limiares de detecção de borda, taxa de amostragem, ROI…) afetam o
erro das grandezas modais estimadas. Veja o [ROADMAP](ROADMAP.md).

---

## Como funciona

```
vídeo ──► recorte da ROI ──► borda superior sub-pixel ──► matriz espaço-tempo Y(t, x)
                             (Sobel-Y + interpolação       (deslocamento em mm,
                              parabólica, por coluna)        lacunas interpoladas)
                                                                    │
                                                                   SVD
                                                ┌───────────────────┴───────────────────┐
                                           U[:,0] (tempo)                          Vt[0,:] (espaço)
                                                │                                       │
                                               FFT                        Savitzky-Golay + ajuste
                                                │                           A·sin(πx/L+φ)+C  (R²)
                                     frequência fundamental                       forma modal
```

1. **Detecção de borda** — para cada coluna da ROI, o gradiente vertical (Sobel-Y sobre
   imagem suavizada) é limiarizado; o primeiro pico local é a borda superior da viga, refinada
   para precisão sub-pixel por interpolação parabólica.
2. **Série temporal** — os pontos de cada coluna formam uma série no tempo; frames sem
   detecção são preenchidos (spline cúbica), a média temporal é subtraída (deslocamento) e o
   resultado é convertido para mm com um fator de escala calibrado por uma altura conhecida.
3. **Análise modal** — a SVD da matriz `Y` separa o movimento estrutural dominante do ruído.
   O 1º vetor singular temporal alimenta a FFT; o 1º vetor espacial é a forma modal, comparada
   ao 1º modo teórico de uma viga biapoiada.
4. **Saída** — por vídeo, em `frames_saida/<nome_do_vídeo>/`: CSVs (`dados_vibracao.csv`,
   `matriz_deslocamentos.csv`), gráficos HTML interativos (integridade dos dados, espectro FFT,
   forma modal), planilha XLSX da forma modal e imagens de verificação.

Detalhes de arquitetura em [docs/arquitetura.md](docs/arquitetura.md).

## Instalação

Requer Python 3.10+.

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

## Uso

### Interface gráfica

Rode de dentro de `app_final/` (os módulos se importam pelo nome e a saída vai para
`./frames_saida`):

```powershell
cd app_final
..\.venv\Scripts\python main.py
```

Na janela:

| Campo | Significado |
|---|---|
| Vídeo(s) | Um ou mais vídeos; cada um é processado e salvo em sua própria subpasta |
| Taxa de extração | Processa 1 a cada *N* frames (1 = todos) |
| FPS | FPS real da câmera (padrão 440). Vazio = lê do arquivo. **Essencial para o eixo de frequência** |
| Corte inicial | Segundos iniciais descartados (transientes, mão do operador) |
| ROI | Região da viga, em **% do frame** (x1, x2, y1, y2), com preview |
| Escala | Região de altura conhecida da viga (mm) para o fator mm/px, com preview |

> ⚠️ Cada execução **apaga** a subpasta de saída do vídeo antes de começar.

### Teste de fumaça (sem GUI)

Processa `vídeos exemplo para reunião/1a freq.mp4` (na raiz do projeto, fora do repo) e
confere se todas as saídas foram geradas:

```powershell
cd app_final
..\.venv\Scripts\python -X utf8 test_headless.py [caminho_do_video]
```

## Estrutura do repositório

```
app_final/                  aplicativo
  main.py                   entrada Tkinter, orquestração, thread de processamento
  widgets.py                componentes de interface (ROI, escala, campos)
  tools.py                  laço de leitura do vídeo, I/O, calibração de escala
  data_extraction.py        detector de borda sub-pixel e série temporal
  structural_modal_analysis.py  SVD, FFT, forma modal, ajuste teórico
  data_visualization.py     gráficos Plotly e exportação XLSX
  test_headless.py          teste de fumaça
docs/                       documentação técnica e notas metodológicas
ROADMAP.md                  plano de desenvolvimento
requirements.txt
```

Vídeos e resultados **não** são versionados (são grandes): ficam fora deste repositório.

## Dados experimentais

Gravações com câmera Basler acA640-750uc a 440 fps, viga excitada por shaker, em três
distâncias da câmera (155, 215 e 290 cm) e dois enquadramentos (shaker e centro do vão).

## Estado

Pipeline funcional de ponta a ponta. Limitações conhecidas e próximos passos no
[ROADMAP](ROADMAP.md).
