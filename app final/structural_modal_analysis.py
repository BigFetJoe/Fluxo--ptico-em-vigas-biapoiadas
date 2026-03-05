import numpy as np
import pandas as pd
from scipy.fft import fft, fftfreq
from scipy.linalg import svd

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
    Extrai a forma modal contendo o envelope de deslocamentos máximos em mm ao longo do comprimento (x_px).
    """
    if df.empty or 'displacement_mm' not in df.columns:
        return pd.DataFrame()

    # Encontra o deslocamento (absoluto) máximo para cada posição X na viga
    df_abs = df.copy()
    df_abs['abs_displacement_mm'] = df_abs['displacement_mm'].abs()
    
    forma_modal = df_abs.groupby('posicao_x_pixels', as_index=False)['abs_displacement_mm'].max()
    forma_modal = forma_modal.sort_values('posicao_x_pixels')
    
    # Renomeia para fazer sentido com "amplitude do modo"
    forma_modal.rename(columns={'abs_displacement_mm': 'modal_amplitude_mm'}, inplace=True)
    
    return forma_modal


def calcular_curvatura_modal(shape_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula a curvatura modal usando a derivada espacial de segunda ordem (diferenças finitas completas).
    Recebe o dataframe resultante da função `extrair_forma_modal`.
    """
    if shape_df.empty or len(shape_df) < 3:
        # Se não houver pontos suficientes para fazer a derivada 2D, retorna vazio ou zeros.
        return shape_df

    # Converter para arrays do numpy para conta mais rápida
    x = shape_df['posicao_x_pixels'].values
    w = shape_df['modal_amplitude_mm'].values
    
    # Array de resposta para curvatura
    curvatura = np.zeros_like(w)
    
    # Diferenças Frequentes Finitas Centrais (Apenas para nós internos)
    # Curvatura(x_i) = ( w(x_i+1) - 2w(x_i) + w(x_i-1) ) / (delta_x)^2
    
    # Nota: Como posicao_x_pixels pode não ter um passo uniformemente espaçado (ex: se um ponto falhar sempre), 
    # teremos que usar uma média do delta X ou a fórmula genérica matemática. 
    # Assumindo grade razoavelmente uniforme para simplificar por enquanto.
    for i in range(1, len(x) - 1):
        dx_frente = x[i+1] - x[i]
        dx_tras = x[i] - x[i-1]
        dx_medio = (dx_frente + dx_tras) / 2.0
        
        # Evitar divisão por zero caso haja Xs duplicados acidentalmente
        if dx_medio > 0:
            curvatura[i] = (w[i+1] - 2*w[i] + w[i-1]) / (dx_medio**2)
            
    # Bordas (i=0 e i=len-1) receberão a curvatura do vizinho mais próximo como extrapolação básica
    curvatura[0] = curvatura[1]
    curvatura[-1] = curvatura[-2]
    
    shape_df['modal_curvature'] = curvatura
    
    return shape_df
