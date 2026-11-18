import numpy as np
import pandas as pd
from scipy.fft import fft, fftfreq
from scipy.linalg import svd
from scipy.signal import savgol_filter
from scipy.optimize import curve_fit
from sklearn.metrics import r2_score

# Este módulo é focado no processamento e análise do comportamento estrutural e dinâmico da viga.
# Suas funções principais incluem o cálculo da frequência natural fundamental através da FFT, 
# a extração da forma modal e o cálculo da curvatura modal usando diferenças finitas.


from typing import Tuple

def calcular_frequencia_natural(df: pd.DataFrame, fps: float, video_name: str = "") -> Tuple[float, np.ndarray, np.ndarray]:
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
        
        # --- CÁLCULO DA RAZÃO DE VARIÂNCIA EXPLICADA (EVR) ---
        energia_total = np.sum(S_vals**2)
        energia_1 = S_vals[0]**2
        evr_1 = (energia_1 / energia_total) * 100
        
        if video_name:
            print(f"[{video_name}] Energia do 1º componente (SVD): {evr_1:.2f}%")
        else:
            print(f"Energia do 1º componente (SVD): {evr_1:.2f}%")
        
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


def extrair_forma_modal(df: pd.DataFrame, video_name: str = "") -> pd.DataFrame:
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
        
        # --- CÁLCULO DA RAZÃO DE VARIÂNCIA EXPLICADA (EVR) ---
        energia_total = np.sum(S_vals**2)
        energia_1 = S_vals[0]**2
        evr_1 = (energia_1 / energia_total) * 100
        
        if video_name:
            print(f"[{video_name}] Energia do 1º componente (SVD): {evr_1:.2f}%")
        else:
            print(f"Energia do 1º componente (SVD): {evr_1:.2f}%")
        
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


def suavizar_forma_modal(shape_df: pd.DataFrame, window_length: int = 51, polyorder: int = 3) -> pd.DataFrame:
    """
    Suaviza a forma modal calculada utilizando o filtro Savitzky-Golay, retendo apenas a linha azul de amplitude.
    """
    if shape_df.empty or len(shape_df) < 3:
        # Se não houver pontos suficientes, não há como suavizar
        return shape_df

    # Garantir janela ímpar e menor/igual ao tamanho dos dados
    n_pontos = len(shape_df)
    if window_length > n_pontos:
        window_length = n_pontos if n_pontos % 2 != 0 else n_pontos - 1
    elif window_length % 2 == 0:
        window_length += 1

    # Extrair os arrays
    y = shape_df['modal_amplitude_mm'].values
    
    # Suavização inicial da forma modal para o gráfico (Savitzky-Golay)
    # y_alisado será a nossa "linha azul" principal
    y_alisado = savgol_filter(y, window_length=window_length, polyorder=polyorder)
    shape_df['modal_amplitude_mm'] = y_alisado # Atualiza a forma modal para plotagem mais orgânica
    
    return shape_df

from typing import Tuple

def _funcao_teorica_viga_biapoiada(x, A, L, phi, C):
    """
    Função teórica para o 1º modo de vibração de uma viga biapoiada (Simply Supported).
    y(x) = A * sin(pi * x / L + phi) + C
    L = comprimento total da onda
    A = Amplitude Máxima
    phi = Phase shift
    C = Offset Vertical
    """
    return A * np.sin(np.pi * x / L + phi) + C

def ajustar_curva_teorica(shape_df: pd.DataFrame) -> Tuple[pd.DataFrame, float]:
    """
    Ajusta a forma modal suavizada experimental a uma onda senoidal teórica (Viga Biapoiada, 1º Modo).
    Retorna o DataFrame modificado com a coluna 'modal_teorica_mm' e o coeficiente R² do ajuste.
    """
    if shape_df.empty or len(shape_df) < 3 or 'modal_amplitude_mm' not in shape_df.columns:
        shape_df['modal_teorica_mm'] = shape_df.get('modal_amplitude_mm', 0.0)
        return shape_df, 0.0
        
    x_data = shape_df['posicao_x_pixels'].values
    y_data = shape_df['modal_amplitude_mm'].values
    
    # Estimativas iniciais (Chutes) para o curve_fit convergir bem
    x_min, x_max = x_data.min(), x_data.max()
    L_guess = x_max - x_min if x_max > x_min else 1.0 # Aproximadamente a tela toda
    
    # Prepara o X transladado para o fit numérico ficar mais estável
    x_norm = x_data - x_min
    
    A_guess = np.max(np.abs(y_data)) # Amplitude máxima
    # Ajuste de sinal inicial baseado se a "barriga" é para cima ou para baixo
    meio_real = np.mean(y_data)
    if meio_real < 0:
        A_guess = -A_guess
        
    C_guess = y_data[0] # Começa no offset do começo da viga
    phi_guess = 0.0
    
    p0 = [A_guess, L_guess, phi_guess, C_guess]
    
    bounds = (
        [-np.inf, L_guess * 0.5, -np.pi, -np.inf],
        [np.inf, L_guess * 3.0, np.pi, np.inf]
    )
    
    try:
        popt, pcov = curve_fit(_funcao_teorica_viga_biapoiada, x_norm, y_data, p0=p0, bounds=bounds, maxfev=10000)
        y_teorico = _funcao_teorica_viga_biapoiada(x_norm, *popt)
        
        # Calcular R2 score
        r2 = r2_score(y_data, y_teorico)
        
        shape_df['modal_teorica_mm'] = y_teorico
        return shape_df, r2
    except Exception as e:
        print(f"Erro ao ajustar curva teórica: {e}")
        # Retorna R2 zero e usa a própria curva como fallback
        shape_df['modal_teorica_mm'] = np.nan
        return shape_df, 0.0
