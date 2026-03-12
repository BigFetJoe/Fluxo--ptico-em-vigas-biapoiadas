import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# arquivo de visualização de dados: gráficos 2D e 3D


from plotly.subplots import make_subplots
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import structural_modal_analysis as sma


def plot_data_integrity(df: pd.DataFrame, pasta_saida: str):
    """
    Gera um gráfico de barras ao longo de $X$ demonstrando a métrica 
    de "confiabilidade" e destacando os frames de erro. 
    Salva como HTML interativo.
    """
    if df.empty or 'posicao_x_pixels' not in df.columns or 'confiabilidade' not in df.columns:
        return
        
    df_agrupado = df.groupby('posicao_x_pixels', as_index=False)['confiabilidade'].mean()
    
    fig = px.bar(
        df_agrupado, 
        x='posicao_x_pixels', 
        y='confiabilidade',
        title="Integridade dos Dados Extraídos (Confiabilidade por Ponto X)",
        labels={'posicao_x_pixels': 'Posição na Viga (Pixels)', 'confiabilidade': 'Leitura Válida (%)'},
        color='confiabilidade',
        color_continuous_scale=[(0, "red"), (0.5, "yellow"), (1, "green")]
    )
    
    fig.update_layout(yaxis_range=[0, 105])
    
    caminho_html = os.path.join(pasta_saida, "integridade_dados.html")
    fig.write_html(caminho_html)
    print(f"Gráfico salvo em: {caminho_html}")


def plot_natural_frequency(df: pd.DataFrame, fps: float, pasta_saida: str):
    """
    Gera um gráfico do domínio das frequências (Espectro FFT) indicando 
    o pico ressonante fundamental calculado em structural_modal_analysis.py.
    """
    freq_fundamental_hz, frequencias_hz, espectro_magnitude = sma.calcular_frequencia_natural(df, fps)
    
    if len(frequencias_hz) == 0 or len(espectro_magnitude) == 0:
        return
        
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=frequencias_hz, 
        y=espectro_magnitude, 
        mode='lines', 
        name='Espectro de Magnitude',
        line=dict(color='royalblue')
    ))
    
    # Destacar a frequência fundamental
    if freq_fundamental_hz > 0:
        idx_pico = list(frequencias_hz).index(freq_fundamental_hz)
        mag_pico = espectro_magnitude[idx_pico]
        
        fig.add_trace(go.Scatter(
            x=[freq_fundamental_hz], 
            y=[mag_pico], 
            mode='markers+text', 
            name='Frequência Fundamental',
            marker=dict(color='red', size=10, symbol='x'),
            text=[f'{freq_fundamental_hz:.2f} Hz'],
            textposition="top center"
        ))
    
    fig.update_layout(
        title="Espectro de Frequência (FFT) - Identificação Modal",
        xaxis_title="Frequência (Hz)",
        yaxis_title="Magnitude",
        xaxis_range=[0, fps/2.0] # Até Nyquist limit
    )
    
    caminho_html = os.path.join(pasta_saida, "frequencia_natural_FFT.html")
    fig.write_html(caminho_html)
    print(f"Gráfico salvo em: {caminho_html}")


def plot_modal_shape_and_curvature(df: pd.DataFrame, scale_factor: float, pasta_saida: str):
    """
    Gera uma exibição combinada em 2D de eixos duplos: 
    o formato deformado da viga (Forma Modal) e a Curvatura Modal.
    """
    forma_df = sma.extrair_forma_modal(df)
    curvatura_df = sma.calcular_curvatura_modal(forma_df, scale_factor=scale_factor)
    
    if curvatura_df.empty:
        return
        
    # Cria os suplots com Double Y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Adicionar o traço da Forma Modal (Left Y Axis)
    fig.add_trace(
        go.Scatter(
            x=curvatura_df['posicao_x_pixels'], 
            y=curvatura_df['modal_amplitude_mm'],
            mode='lines+markers',
            name="Forma Modal (Max deslocamento em mm)",
            line=dict(color='blue', width=2),
            marker=dict(size=6)
        ),
        secondary_y=False,
    )
    
    # Adicionar o traço da Curvatura Modal (Right Y Axis)
    if 'modal_curvature' in curvatura_df.columns:
        fig.add_trace(
            go.Scatter(
                x=curvatura_df['posicao_x_pixels'], 
                y=curvatura_df['modal_curvature'],
                mode='lines+markers',
                name="Curvatura Modal (1/mm)",
                line=dict(color='red', width=2, dash='dot'),
                marker=dict(size=6, symbol='square')
            ),
            secondary_y=True,
        )
        
    fig.update_layout(
        title_text="Análise de Dano: Forma e Curvatura Modal",
        hovermode="x unified"
    )
    
    # Atualizar títulos dos eixos
    fig.update_xaxes(title_text="Posição na Viga (Pixels)")
    fig.update_yaxes(title_text="Deslocamento (mm)", secondary_y=False)
    fig.update_yaxes(title_text="Curvatura Modal (1/mm)", secondary_y=True)

    caminho_html = os.path.join(pasta_saida, "forma_e_curvatura_modal.html")
    fig.write_html(caminho_html)
    print(f"Gráfico salvo em: {caminho_html}")
