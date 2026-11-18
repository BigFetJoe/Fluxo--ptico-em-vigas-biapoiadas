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


def plot_natural_frequency(df: pd.DataFrame, fps: float, pasta_saida: str, video_name: str = ""):
    """
    Gera um gráfico do domínio das frequências (Espectro FFT) indicando 
    o pico ressonante fundamental calculado em structural_modal_analysis.py.
    """
    freq_fundamental_hz, frequencias_hz, espectro_magnitude = sma.calcular_frequencia_natural(df, fps, video_name)
    
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


def plot_modal_shape(df: pd.DataFrame, pasta_saida: str, video_name: str = ""):
    """
    Gera uma exibição em 2D do formato deformado da viga (Forma Modal).
    Mostra a linha azul com a amplitude maxima e uma linha pontilhada verde 
    indicando a curva teórica esperada (esperado perfeito), junto do R².
    """
    forma_df = sma.extrair_forma_modal(df, video_name)
    forma_suavizada_df = sma.suavizar_forma_modal(forma_df)
    
    # Gerar a curva teórica e calcular o R2 (Para a viga Biapoiada)
    forma_suavizada_df, r2_score = sma.ajustar_curva_teorica(forma_suavizada_df)
    
    if forma_suavizada_df.empty:
        return
        
    fig = go.Figure()
    
    # Adicionar o traço da Forma Modal (Experimental Suavizada)
    fig.add_trace(
        go.Scatter(
            x=forma_suavizada_df['posicao_x_pixels'], 
            y=forma_suavizada_df['modal_amplitude_mm'],
            mode='lines+markers',
            name="Forma Modal Experimental",
            line=dict(color='blue', width=2),
            marker=dict(size=6)
        )
    )
    
    # Adicionar o traço da Curva Teórica (Esperado Perfeito)
    if 'modal_teorica_mm' in forma_suavizada_df.columns and not forma_suavizada_df['modal_teorica_mm'].isna().all():
        fig.add_trace(
            go.Scatter(
                x=forma_suavizada_df['posicao_x_pixels'], 
                y=forma_suavizada_df['modal_teorica_mm'],
                mode='lines',
                name="Teórica (Esperado Perfeito)",
                line=dict(color='green', width=2, dash='dash')
            )
        )
        
    # Anotação com o R2
    if r2_score is not None:
        fig.add_annotation(
            text=f"<b>R²: {r2_score:.4f}</b>",
            xref="paper", yref="paper",
            x=0.05, y=0.95, showarrow=False,
            font=dict(size=14, color="black"),
            bgcolor="white", bordercolor="black", borderwidth=1
        )
        
    fig.update_layout(
        title_text=f"Análise de Dano: Forma Modal (R² = {r2_score:.4f})",
        hovermode="x unified",
        xaxis_title="Posição na Viga (Pixels)",
        yaxis_title="Deslocamento (mm)"
    )

    # Exporta para XLSX os dados de deformação (bruta, suavizada, teórica) e o R²
    caminho_xlsx = os.path.join(pasta_saida, "forma_modal_deslocamento_max.xlsx")
    
    # Preparar DataFrame de export
    colunas_export = ['posicao_x_pixels', 'displacement_mm', 'modal_amplitude_mm']
    nomes_colunas = ['Posicao_X_Pixels', 'Desloc_Bruto_mm', 'Desloc_Experimental_Suavizado_mm']
    
    if 'modal_teorica_mm' in forma_suavizada_df.columns:
         colunas_export.append('modal_teorica_mm')
         nomes_colunas.append('Desloc_Teorico_Perfeito_mm')
         
    df_export = forma_suavizada_df[colunas_export].copy()
    df_export.columns = nomes_colunas
    
    # Adicionar o valor de R2 como uma meta-informação na própria tabela para fácil leitura
    df_export['R2_Score_Global'] = r2_score
    
    try:
        df_export.to_excel(caminho_xlsx, index=False)
        print(f"Dados da forma modal salvos em Excel: {caminho_xlsx} (R²: {r2_score:.4f})")
    except ModuleNotFoundError:
        print("Módulo 'openpyxl' não instalado. Salvando como CSV de fallback...")
        caminho_csv = caminho_xlsx.replace('.xlsx', '.csv')
        df_export.to_csv(caminho_csv, index=False, sep=';', decimal=',')
        print(f"Dados da forma modal salvos em CSV: {caminho_csv}")

    caminho_html = os.path.join(pasta_saida, "forma_modal.html")
    fig.write_html(caminho_html)
    print(f"Gráfico salvo em: {caminho_html}")

