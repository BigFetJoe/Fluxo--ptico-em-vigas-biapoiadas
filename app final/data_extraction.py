import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Protocol, Tuple, Optional, Any
import os
import cv2

# arquivo de processamento de dados:
# importa de tools e realmente efetua o processamento com os frames do vídeo vindos do widget

@dataclass
class FrameData:
    """
    Data structure representing the extraction result from a single frame.
    """
    frame_index: int
    timestamp: float
    # List of (x, y) points found on the top edge
    # Using float because sub-pixel detection might return non-integers
    edge_points: List[Tuple[float, float]] = field(default_factory=list)

@dataclass
class PointData:
    x_coord: int  # Posição fixa X na imagem (em pixels)
    y_values: List[float] = field(default_factory=list) # O deslocamento y encontrado
    timestamps: List[float] = field(default_factory=list) # O tempo exato
    
    # Novos atributos de rastreamento de confiabilidade
    leituras_validas: int = 0
    frames_invalidos: List[int] = field(default_factory=list)
    confiabilidade: float = 0.0


class EdgeDetector:
    """
    Edge detector using Sobel Y gradient and parabolic interpolation for sub-pixel precision.
    Substitui a versão baseada em cv2.Canny.
    """
    def __init__(self, step: int = 2, grad_threshold: float = 30.0):
        self.step = step
        self.grad_threshold = grad_threshold

    def detect(self, image_roi: np.ndarray) -> Tuple[List[Tuple[float, float]], np.ndarray]:
        # Aplicar blur para atenuar ruído de alta frequência
        blur = cv2.GaussianBlur(image_roi, (5, 5), 0)
        
        # Gradiente vertical com Sobel (64-bit float para precisão)
        grad_y = cv2.Sobel(blur, cv2.CV_64F, 0, 1, ksize=3)
        grad_abs = np.abs(grad_y)
        
        h, w = image_roi.shape
        pontos = []
        
        for x in range(0, w, self.step):
            col_grad = grad_abs[:, x]
            
            # Localizar índices onde o gradiente passa do limiar estipulado
            ys = np.where(col_grad > self.grad_threshold)[0]
            if len(ys) == 0:
                continue
                
            # Procurar o primeiro pico local que represente a borda superior
            y_peak = -1
            for y in ys:
                if 0 < y < h - 1:
                    # Condição de pico local
                    if col_grad[y] >= col_grad[y-1] and col_grad[y] >= col_grad[y+1]:
                        y_peak = y
                        break
                        
            if y_peak == -1:
                # Fallback: pega a primeira amostra acima do threshold que não caiba num pico ideal
                y_peak = ys[0]
                if y_peak <= 0 or y_peak >= h - 1:
                    pontos.append((float(x), float(y_peak)))
                    continue
                    
            # Interpolação parabólica (fórmula de sub-pixel)
            g1 = col_grad[y_peak - 1]
            g2 = col_grad[y_peak]
            g3 = col_grad[y_peak + 1]
            
            denominador = (g1 - 2*g2 + g3)
            if denominador != 0:
                # O ajuste de sub-pixel na grade do pixel base y_peak
                offset = 0.5 * (g1 - g3) / denominador
                sub_y = float(y_peak) + offset
            else:
                sub_y = float(y_peak)
                
            pontos.append((float(x), sub_y))
            
        # Gera a imagem de visualização
        img_vis = cv2.cvtColor(image_roi, cv2.COLOR_GRAY2BGR)
        for p in pontos:
            # Desenha em vermelho os pontos encontrados (arredondando apenas pra tela)
            cv2.circle(img_vis, (int(p[0]), int(round(p[1]))), 1, (0, 0, 255), -1)
            
        return pontos, img_vis

class VibrationTimeSeries:
    """
    Core class to accumulate vibration data and handle physical conversions.
    Agora baseada em pontos (PointData) no lugar de frames.
    """
    def __init__(self, fps: float = 30.0, scale_factor: float = 1.0):
        """
        :param fps: Frames per second of the video.
        :param scale_factor: Conversion factor (e.g., mm per pixel). 1.0 means data is in pixels.
        """
        self.fps = fps
        self.scale_factor = scale_factor
        
        # Armazenamento orientado a coordenada X
        # chave: x (int), valor: PointData
        self.points_store: dict[int, PointData] = {}
        
        # Manter controle do tempo global para evitar problemas de dados ausentes (missing data)
        self.global_timestamps: set[float] = set()

    def add_frame(self, frame_idx: int, points: List[Tuple[float, float]]):
        """
        Registers data for a specific frame, distributing it to individual points.
        """
        timestamp = frame_idx / self.fps
        self.global_timestamps.add(timestamp)
        
        # Coleta todas os X detectados neste frame
        detected_xs = set(int(p[0]) for p in points)

        for x, y in points:
            x_int = int(x)
            
            # Se a coluna X for nova, cria a lixeirinha dela
            if x_int not in self.points_store:
                self.points_store[x_int] = PointData(x_coord=x_int)
                
            self.points_store[x_int].timestamps.append(timestamp)
            self.points_store[x_int].y_values.append(y)
            self.points_store[x_int].leituras_validas += 1

        # Trata leitura inválida para os X que já conhecemos mas que não foram detectados AGORA
        for known_x in self.points_store.keys():
            if known_x not in detected_xs:
                self.points_store[known_x].frames_invalidos.append(frame_idx)

    def to_dataframe(self) -> pd.DataFrame:
        """
        Exports the accumulated data to a pandas DataFrame.
        Transações orientadas a coluna e preenchimento de furos ("buracos").
        """
        if not self.points_store or not self.global_timestamps:
            return pd.DataFrame()
            
        # Cria um DataFrame base apenas com a dimensão Tempo garantida.
        sorted_timestamps = sorted(list(self.global_timestamps))
        df_base = pd.DataFrame({"time_sec": sorted_timestamps})
        
        # Para montar as dezenas de gráficos em 3D, Plotly e Pandas usam melhor o formato
        # 'Melted' (ou Long format). Faremos um Series de cada X intercalado com seu tempo
        records = []
        
        for x_coord, point_data in self.points_store.items():
            if not point_data.y_values:
                continue
                
            # Calcula a confiabilidade independentemente
            total_frames = point_data.leituras_validas + len(point_data.frames_invalidos)
            if total_frames > 0:
                point_data.confiabilidade = (point_data.leituras_validas / total_frames) * 100
            else:
                point_data.confiabilidade = 0.0

            # --- (COMENTADO CONFORME PEDIDO) LÓGICA DE DETECÇÃO DE BAIXA CONFIABILIDADE ---
            # if point_data.confiabilidade < 50.0:  # Exemplo: descarta se menor que 50%
            #     # Poderíamos dar 'continue' para ignorar o ponto
            #     # continue 
            #     # Ou salvar flag de descarte / cor vermelha para o plot:
            #     # df_merged['plot_color'] = 'red'
            # -------------------------------------------------------------------------------

            # Cria DataFrame temporário para esse ponto X
            df_point = pd.DataFrame({
                "time_sec": point_data.timestamps,
                "y_px": point_data.y_values
            })
            
            # Mescla com o tempo global (garante que todos os tempos existam para este X)
            df_merged = pd.merge(df_base, df_point, on="time_sec", how="left")
            
            # Interpolação por spline cúbico para cobrir os quadros que falharam (apenas sobre dados da própria linha de tempo)
            # Preenche primeiro dados faltantes com spline se possível
            if df_merged['y_px'].notna().sum() > 3:  # spline cubic requer pelo menos 4 pontos
                df_merged['y_px'] = df_merged['y_px'].interpolate(method='spline', order=3)
            else:
                df_merged['y_px'] = df_merged['y_px'].interpolate(method='linear')
            
            # Se ainda sobrou nulo (no começo ou fim do vídeo que spline/linear não pegam pra não extrapolar loucamente), joga pro valor mais próximo
            df_merged['y_px'] = df_merged['y_px'].bfill().ffill()
            
            # Agora calcula a média inicial (posição estática - y_mean)
            y_mean = df_merged['y_px'].mean()
            
            # Tendo o y_mean isolado da coluna do X, calcula o deslocamento pra essa fatia
            df_merged['displacement_px'] = df_merged['y_px'] - y_mean
            df_merged['displacement_mm'] = df_merged['displacement_px'] * self.scale_factor
            
            # Anexa as chaves em toda a coluna temporária para identificar o ponto e seus dados
            df_merged['posicao_x_pixels'] = x_coord
            df_merged['confiabilidade'] = point_data.confiabilidade
            df_merged['leituras_validas'] = point_data.leituras_validas
            df_merged['frames_invalidos'] = str(point_data.frames_invalidos)
            
            # Adiciona esses frames já descontados e preenchidos na lista de registros finais
            records.append(df_merged)
            
        # Junta todos os Series de X em um único DataFrame longo novamente     
        if records:
            df_final = pd.concat(records, ignore_index=True)
            return df_final
        else:
            return pd.DataFrame()

    def save_csv(self, filepath: str):
        """
        Persists data to CSV.
        """
        df = self.to_dataframe()
        if not df.empty:
            df.to_csv(filepath, index=False)
            print(f"Data successfully saved to {filepath}")
        else:
            print("No data to save.")
