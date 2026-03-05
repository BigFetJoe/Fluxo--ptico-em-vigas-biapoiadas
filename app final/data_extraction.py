import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Protocol, Tuple, Optional, Any
import os

# arquivo de processamento de dados:
# importa de tools e realmente efetua o processamento com os frames do vídeo vindos do widget

@dataclass
class FrameData:
    """
    Data structure representing the extraction result from a single frame.
    """
    frame_index: int
    timestamp: float
    # List of (x, y) points found on the neutral line
    # Using float because sub-pixel detection might return non-integers
    neutral_points: List[Tuple[float, float]] = field(default_factory=list)

@dataclass
class PointData:
    x_coord: int  # Posição fixa X na imagem (em pixels)
    y_values: List[float] = field(default_factory=list) # O deslocamento y encontrado
    timestamps: List[float] = field(default_factory=list) # O tempo exato
    
    # Novos atributos de rastreamento de confiabilidade
    leituras_validas: int = 0
    frames_invalidos: List[int] = field(default_factory=list)
    confiabilidade: float = 0.0


class EdgeDetector(Protocol):
    """
    Protocol (Interface) for edge detection algorithms.
    This allows us to swap Canny for Sub-pixel methods later without changing the main loop.
    """
    def detect(self, image_roi: np.ndarray) -> Any:
        # Returns an edge map or similar structure suitable for line extraction
        ...

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
