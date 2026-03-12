import numpy as np
import pandas as pd
from scipy.fft import fft, fftfreq
from scipy.linalg import svd
from scipy.signal import savgol_filter

# Este módulo é focado no processamento e análise do comportamento estrutural e dinâmico da viga.
# Suas funções principais incluem o cálculo da frequência natural fundamental através da FFT, 
# a extração da forma modal e o cálculo da curvatura modal usando diferenças finitas.


from typing import Tuple

def calcular_frequencia_natural(df: pd.DataFrame, fps: float) -> Tuple[float, np.ndarray, np.ndarray]:
    """
    Calcula a frequência natural fundamental (em Hz) utilizando a Transformada Rápida de Fourier (FFT)
    após agregação da matriz espaço-tempo com Decomposição em Valores Singulares (SVD).
    Retorna uma tupla contendo: (frequencia_fundamental_hz, frequencias_hz, espectro_magnitude)
    """
    if df.empty or 'displacement_mm' not in df.columns or 'time_sec' not in df.columns:
        return 0.0, np.array([]), np.array([])

    # 1. Pivotar o DataFrame para construir a matriz Espaço(X)-Tempo(Y)
    matriz_df = df.pivot(index='time_sec', columns='posicao_x_pixels', values='displacement_mm')
    
    # 2. Utilizar interpolação para preencher valores vazios na matriz
    # Primeiro interpola linearmente (dentro de cada coluna), depois copia pros cantos (bfill/ffill)
    matriz_df = matriz_df.interpolate(method='linear', axis=0).bfill(axis=0).ffill(axis=0)
    
    # Caso alguma coluna fique inteira vazia (mesmo após os fills), colocar zeros na matriz
    matriz_df = matriz_df.fillna(0.0)
    
    # Extrai os valores numéricos como a Matriz Y
    Y = matriz_df.values
    
    # 3. Remover valor médio (DC Offset) global baseado na média temporal de cada posição X
    Y_mean = np.mean(Y, axis=0)
    Y_centered = Y - Y_mean
    
    # Previne erro se a matriz for muito muito ínfima (menos de 2 pontos lidos total)
    if min(Y_centered.shape) < 2:
        sinal_principal = Y_centered[:, 0] if Y_centered.shape[1] > 0 else np.zeros(Y_centered.shape[0])
    else:
        # 4. Decomposição em Valores Singulares (SVD: Y = U * S * V^T)
        # O parâmetro full_matrices=False é para extrair forma otimizada de U (T x min(T, N))
        U, S_vals, Vt = svd(Y_centered, full_matrices=False)
        
        # O ruído foi filtrado para as caudas do SVD. Pegamos o Principal Componente Espaço-Temporal:
        # A 1ª coluna de U (U[:, 0]) guarda a dinâmica predominante (Shape Modificado x Ritmo).
        # Multiplicamos pelo 1º valor singular (S_vals[0]) para restaurar proporção de amplitude do sinal global
        sinal_principal = U[:, 0] * S_vals[0]
    
    # 5. Aplicação da FFT sobre o Sinal Principal Global extraído
    N = len(sinal_principal)
    if N == 0:
        return 0.0, np.array([]), np.array([])
        
    T = 1.0 / fps
    
    # Calcula a FFT final apenas no melhor modo global unificado
    espectro_magnitude = fft(sinal_principal)
    frequencias_hz = fftfreq(N, T)[:N//2]
    
    # Pegamos apenas a parte real/positiva da magnitude
    espectro_magnitude = np.abs(espectro_magnitude[0:N//2])
    
    # O pico de maior magnitude representa a frequência fundamental desta malha
    if len(espectro_magnitude) > 0:
        idx_pico = np.argmax(espectro_magnitude)
        freq_fundamental_hz = frequencias_hz[idx_pico]
    else:
        freq_fundamental_hz = 0.0
        
    # implementar aqui deteção de modos superiores usando encontrar picos locais no espectro ('scipy.signal.find_peaks' por exemplo)
    
    return freq_fundamental_hz, frequencias_hz, espectro_magnitude


def extrair_forma_modal(df: pd.DataFrame) -> pd.DataFrame:
    """
    1. Constrói a Matriz Global Espaço-Tempo (2D Densa).
    2. Aplica a Decomposição em Valores Singulares (SVD).
    3. Extrai o Componente Principal Espacial (Modo Fundamental) blindado contra ruídos.
    """
    if df.empty or 'displacement_mm' not in df.columns or 'time_sec' not in df.columns:
        return pd.DataFrame()

    # 1. Cria matriz pivotada (Linhas = Tempo, Colunas = Posição X)
    matriz_df = df.pivot(index='time_sec', columns='posicao_x_pixels', values='displacement_mm')
    
    # Preenchimentos básicos de vazios
    matriz_df = matriz_df.interpolate(method='linear', axis=0).bfill(axis=0).ffill(axis=0).fillna(0.0)
    
    # Extrai array numérico
    Y = matriz_df.values
    
    # Remove a média de cada coluna (offset estático)
    Y_mean = np.mean(Y, axis=0)
    Y_centered = Y - Y_mean
    
    # Previne erro se a matriz for mínima
    if min(Y_centered.shape) < 2:
        forma_bruta = Y_centered[0, :] if Y_centered.shape[0] > 0 else np.zeros(Y_centered.shape[1])
    else:
        # 2. Decomposição em Valores Singulares (SVD: Y = U * S * V^T)
        U, S_vals, Vt = svd(Y_centered, full_matrices=False)
        
        # 3. A Forma Modal verdadeira e livre de ruídos é a primeira linha da matriz espacial Vt
        # Multiplicamos pelo 1º valor singular e pela oscilação temporal máxima (U[:, 0]) 
        # para obter a amplitude física máxima do deslocamento em mm a partir do ponto de repouso
        amp_max_temporal = np.max(np.abs(U[:, 0]))
        forma_bruta = Vt[0, :] * S_vals[0] * amp_max_temporal
        
    # Salvar em formato DataFrame (mesmo formato que a versão anterior esperava)
    coords_x = matriz_df.columns.values
    
    # Determinar se a forma extraída está invertida horizontalmente devido à ambiguidade de sinal do SVD
    # Se a deformação principal é para baixo (negativa), mas a SVD cuspiu positiva, ajeitamos para fins estéticos (opcional)
    # Pegamos o sinal da maior correlação com a matriz original
    if len(forma_bruta) > 0:
        correlacao_max = np.mean(Y_centered * forma_bruta, axis=0)
        sinal_predominante = 1 if np.sum(correlacao_max) > 0 else -1
        forma_bruta = forma_bruta * sinal_predominante
        
    df_forma = pd.DataFrame({
        'posicao_x_pixels': coords_x,
        'displacement_mm': forma_bruta,
        'time_sec': [df['time_sec'].iloc[0]] * len(coords_x) # Apenas mantendo a coluna pro cv2 puxar o tempo (mesmo que arbitrário aqui)
    })
    
    # Agora a amplitude modal é o deslocamento físico puro em relação à linha estática.
    # Não forçamos o ponto mais baixo a ser 0, para refletir o comportamento real do segmento visto na câmera.
    df_forma['modal_amplitude_mm'] = df_forma['displacement_mm']
    
    return df_forma


def calcular_curvatura_modal(shape_df: pd.DataFrame, window_length: int = 51, polyorder: int = 3, scale_factor: float = 1.0) -> pd.DataFrame:
    """
    Calcula a curvatura modal reduzida através do método clássico de diferenças finitas centrais.
    Fórmula: \kappa_i = (\phi_{i+1} - 2\phi_i + \phi_{i-1}) / h^2
    """
    if shape_df.empty or len(shape_df) < 3:
        # Se não houver pontos suficientes para a derivada central, não há como calcular
        return shape_df

    # Garantir janela ímpar e menor/igual ao tamanho dos dados
    n_pontos = len(shape_df)
    if window_length > n_pontos:
        window_length = n_pontos if n_pontos % 2 != 0 else n_pontos - 1
    elif window_length % 2 == 0:
        window_length += 1

    # Extrair os arrays
    x = shape_df['posicao_x_pixels'].values
    y = shape_df['modal_amplitude_mm'].values
    
    # Suavização inicial da forma modal para o gráfico (Savitzky-Golay)
    # A diferença finita amplifica muito o ruído se aplicada sobre dados brutos experimentais
    y_alisado = savgol_filter(y, window_length=window_length, polyorder=polyorder)
    shape_df['modal_amplitude_mm'] = y_alisado # Atualiza a forma modal para plotagem mais orgânica
    
    # 1. Definir o vetor espacial (x) corrigido em milímetros reais
    # Para o fit numérico funcionar bem sem problemas de condicionamento (x muito grande),
    # centralizamos o eixo X em zero para o meio da viga e escalamos para mm físicos.
    x_mm = (x - np.mean(x)) * scale_factor
    
    # 2. Ajuste Polinomial Global da Forma Modal (Polynomial Fit)
    # Para formas primárias de Euler-Bernoulli (1º modo biapoiado/engastado),
    # polinômios pares como Grau 4 capturam perfeitamente o arco analítico da estrutura vibrando livre,
    # ignorando instantaneamente os ruídos sub-pixel e tremidas de câmera no ajuste dos mínimos quadrados.
    grau_polinomio = 4 
    
    # y_alisado do filtro pode ser mantido ou podemos ajustar sobre os dados brutos (y). 
    # Aqui ajustamos sobre os alisados inicialmente definidos por legibilidade gráfica na linha azul.
    coeficientes = np.polyfit(x_mm, y_alisado, grau_polinomio)
    
    # 3. Segunda Derivada Algébrica (Curvatura)
    # Como y(x) = p4*x^4 + p3*x^3 + p2*x^2 + p1*x + p0, a segunda derivada (curvatura geométrica k) 
    # é perfeitamente contínua e imune às distâncias h entre os pixels ou instabilidades numéricas
    coeficientes_derivada2 = np.polyder(coeficientes, 2)
    
    # 4. Avaliar o polinômio derivado em cada ponto X do nosso segmento
    curvatura_analitica = np.polyval(coeficientes_derivada2, x_mm)
    
    # Aplicar o mapeamento direto. O sinal geométrico importa, mas as vezes esteticamente (pra plot) o módulo é preferido. 
    # Vamos manter o formalismo da derivada para manter a direção da concavidade fiel.
    shape_df['modal_curvature'] = curvatura_analitica
    
    return shape_df
