# Notas de rigor metodológico

Pontos para fortalecer o artigo de **análise de sensibilidade**. Cada item diz o problema,
por que importa para o revisor e o que fazer. A ordem segue o impacto estimado.

---

## 1. Ter uma referência de erro com valor verdadeiro conhecido

**Problema.** Para medir o "erro em relação à viga perfeita" é preciso saber o valor
verdadeiro. Com vídeo real, a verdade só é conhecida de forma indireta (acelerômetro, modelo
analítico), e as duas têm incerteza própria.

**Proposta — usar três referências complementares:**

| Referência | O que dá | Limitação |
|---|---|---|
| **Vídeo sintético** de uma viga renderizada com deslocamento `w(x,t) = A·sin(πx/L)·sin(2πf t)` conhecido, com borrão, ruído e anti-aliasing controlados | Erro **absoluto** de deslocamento (em px e mm), de frequência e de forma modal, ponto a ponto | Não reproduz iluminação, reflexos e textura reais |
| **Acelerômetro** (ground truth experimental) | Frequência de referência nos ensaios reais | Massa adicional do sensor; posição pontual |
| **Modelo analítico** Euler-Bernoulli: `f₁ = (π / 2L²)·√(EI / ρA)` e `φ₁(x) = sin(πx/L)` | Forma modal teórica e ordem de grandeza da frequência | Depende de E, I, ρ, A, L e da idealização dos apoios |

O vídeo sintético é o que permite uma análise de sensibilidade **limpa**: varia-se um
parâmetro do algoritmo e mede-se o erro contra um valor exato, sem confundir com a variação
do ensaio. Recomenda-se gerar os sintéticos com a mesma resolução, fps e contraste dos vídeos
reais, e varrer também amplitude (sub-pixel até alguns px) e nível de ruído.

## 2. Métricas de erro padronizadas

- **Frequência:** erro relativo `|f̂ − f_ref| / f_ref` (%).
- **Forma modal:** usar o **MAC** (Modal Assurance Criterion), que é o padrão em dinâmica
  estrutural, em vez de (ou além de) R².
  `MAC = |φ̂ᵀφ|² / ((φ̂ᵀφ̂)(φᵀφ))`. Ele não depende da escala nem do sinal da forma.
- **Deslocamento (sintético):** RMSE em px e em mm; erro máximo; viés (média do erro).
- **Qualidade do sinal:** EVR do 1º componente da SVD, SNR do pico espectral, % de pontos
  interpolados.

**Atenção ao R² atual.** O ajuste `A·sin(πx/L+φ)+C` tem 4 parâmetros livres, incluindo `L` e
`φ`. Com essa liberdade, um trecho de senoide se ajusta bem a quase qualquer curva suave, e o
R² fica otimista. Para comparar com a viga biapoiada, `L` e a origem deveriam ser
**fixados** pelas posições dos apoios (em px, ou em mm pela escala). Se a câmera vê só um
trecho do vão, é preciso mapear o x da imagem para a posição física no vão.

## 3. Processamento de sinal

- **Resolução em frequência.** `Δf = fs / N`. Informar Δf em cada resultado. O pico hoje é
  lido no bin da FFT (erro de até Δf/2). Usar **janela de Hann** (reduz vazamento espectral) e
  **interpolação do pico** (parabólica ou Jacobsen), ou zero-padding, para precisão abaixo de
  Δf.
- **Subamostragem e aliasing.** Processar 1 a cada *N* frames reduz a taxa efetiva para
  `fps/N` e o Nyquist para `fps/(2N)`, **sem filtro anti-aliasing**. Frequências acima
  disso reaparecem dobradas no espectro. Se `taxa_extracao` for parâmetro da análise, isso
  precisa ser discutido; o eixo de frequência também precisa usar `fps/N` (ver bug B-11 no
  ROADMAP).
- **Vibração forçada.** Nos ensaios, a viga é excitada por shaker. O pico do espectro é a
  **frequência de excitação**; ela só coincide com a natural se o shaker estiver na
  ressonância. Para frequência natural, preferir decaimento livre (impacto ou desligar o
  shaker) ou varredura senoidal e identificar a ressonância. Deixar isso explícito no texto.
- **FPS real.** O eixo de frequência depende do fps verdadeiro da câmera, não do fps gravado
  no contêiner MP4, que pode ser diferente (ex.: o vídeo `1a freq.mp4` declara 200 fps,
  enquanto os ensaios do dia 2 foram gravados a 440 fps). Conferir com os metadados da câmera
  e registrar a fonte do fps em cada execução.
- **Tendência.** Remover tendência linear (`detrend`) além da média, para evitar vazamento
  de baixa frequência por deriva da câmera ou da iluminação.

## 4. Desenho do experimento de sensibilidade

- **Parâmetros e faixas** definidos antes, com justificativa física (ex.: limiar de gradiente
  em relação ao contraste medido da borda; resolução em px por mm).
- **Um-de-cada-vez (OAT)** é fácil de ler, mas não captura interações (ex.: limiar ótimo
  depende da resolução). Recomenda-se:
  1. **Varredura fatorial** nos 2–3 parâmetros principais (resolução × limiar baixo × limiar
     alto) → mapas de calor de erro;
  2. **Sensibilidade global** (índices de Sobol, ou Morris para triagem) com amostragem Latin
     Hypercube, quando houver mais parâmetros. A biblioteca `SALib` faz isso.
- **Repetições.** Há 2 tomadas por posição e 6 posições. Reportar média ± desvio e intervalo
  de confiança entre tomadas, para separar o efeito do parâmetro da variabilidade do ensaio.
- **Resolução física × digital.** As três distâncias de câmera (155/215/290 cm) já são um
  experimento de resolução **física**. Reduzir a resolução por `cv2.resize(INTER_AREA)` é a
  versão **digital**. Comparar as duas valida se a redução digital é um bom substituto do
  afastamento da câmera.

## 5. Incertezas da medição

- **Escala mm/px.** O fator vem de `h_mm / altura_px`. Propagar a incerteza de `h_mm`
  (paquímetro) e o desvio das alturas medidas por coluna para o deslocamento em mm.
- **Perspectiva e distorção de lente.** Se o eixo óptico não é perpendicular à viga, a escala
  varia ao longo de x. Citar calibração de câmera (tabuleiro de xadrez, `cv2.calibrateCamera`)
  ou justificar que o efeito é desprezível.
- **Lacunas.** Hoje, colunas com falhas de detecção são interpoladas sem critério de
  exclusão. Definir um limiar de confiabilidade (ex.: descartar colunas com < 90 % de leituras
  válidas) e reportar quantas colunas foram excluídas.
- **Precisão sub-pixel.** A interpolação parabólica tem viés conhecido (efeito *pixel-locking*:
  as estimativas se concentram perto de valores inteiros). Medir esse viés com o vídeo
  sintético; considerar ajuste gaussiano ou de centroide como alternativa.

## 6. Reprodutibilidade

- Salvar, a cada execução, um `metadados.json` com: todos os parâmetros, fps e sua fonte,
  fator de escala, versão do código (hash do commit git), versões das bibliotecas, data e
  tempo de processamento.
- Fixar versões no `requirements.txt` na hora de gerar os resultados do artigo.
- Script único (linha de comando) que regenera todas as figuras e tabelas do artigo a partir
  dos vídeos.
- Disponibilizar o código (este repositório) e, se possível, os vídeos (Zenodo ou similar,
  com DOI) e citar no artigo.

## 7. Detector de borda: Sobel × Canny

O detector atual **não é o Canny**: usa Sobel-Y com um único limiar e refinamento
sub-pixel. O Canny tem dois limiares (histerese), afina as bordas, mas sua saída é binária,
com precisão de 1 px. Se o artigo estuda "os dois limites do Canny", há dois caminhos:

1. **Canny para localizar + refinamento sub-pixel no gradiente:** o Canny decide *onde* está
  a borda (com os dois limiares), e a parábola no |grad| refina a posição.
2. **Comparar os dois detectores** como fator da análise: Sobel+parábola × Canny puro ×
  Canny+parábola.

Os dois caminhos deixam o artigo mais forte, porque mostram quanto a precisão sub-pixel
contribui para o erro final.
