import cv2
import os
import numpy as np
import shutil
from tkinter import messagebox

# Funções de limpeza
def limpar_pasta(pasta):
    if os.path.exists(pasta):
        for arquivo in os.listdir(pasta):
            caminho_arquivo = os.path.join(pasta, arquivo)
            try:
                if os.path.isfile(caminho_arquivo) or os.path.islink(caminho_arquivo):
                    os.unlink(caminho_arquivo)
                elif os.path.isdir(caminho_arquivo):
                    shutil.rmtree(caminho_arquivo)
            except Exception as e:
                print(f"Erro ao remover {caminho_arquivo}: {e}")
    else:
        # print(f"A pasta {pasta} não existe.") # debug
        pass

# Funções de IO robustas (Unicode safe)
def smart_imread(path, flag=cv2.IMREAD_GRAYSCALE):
    """Lê imagens suportando caminhos com caracteres especiais/unicode."""
    try:
        data = np.fromfile(path, dtype=np.uint8)
        img = cv2.imdecode(data, flag)
        return img
    except Exception as e:
        print(f"Erro ao ler imagem {path}: {e}")
        return None

def smart_imwrite(path, img):
    """Salva imagens suportando caminhos com caracteres especiais/unicode."""
    try:
        # Pega a extensão do path
        ext = os.path.splitext(path)[1]
        ok, buf = cv2.imencode(ext, img)
        if ok:
            with open(path, "wb") as f:
                f.write(buf)
            return True
        return False
    except Exception as e:
        print(f"Erro ao salvar imagem {path}: {e}")
        return False

### Funções auxiliares para processamento de vídeo e imagens
def _get_roi_coords(shape, roiDict):
    """
    Função auxiliar para calcular coordenadas de pixel a partir de porcentagens.
    """
    h, w = shape[:2]
    
    # Extrai porcentagens
    pct_x1 = roiDict.get('x1', 0)
    pct_x2 = roiDict.get('x2', 100)
    pct_y1 = roiDict.get('y1', 0)
    pct_y2 = roiDict.get('y2', 100)

    # Converte para pixels
    x1 = int((pct_x1 / 100.0) * w)
    x2 = int((pct_x2 / 100.0) * w)
    y1 = int((pct_y1 / 100.0) * h)
    y2 = int((pct_y2 / 100.0) * h)

    # Ordena para evitar coordenadas invertidas
    if x1 > x2: x1, x2 = x2, x1
    if y1 > y2: y1, y2 = y2, y1

    # Garantir limites
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(w, x2)
    y2 = min(h, y2)
    
    return x1, y1, x2, y2

def recortar_roi(img, roiDict):
    """
    img: imagem em escala de cinza (h, w)
    roiDict: {'x1': %, 'x2': %, 'y1': %, 'y2': %}
    Retorna a imagem RECORTADA na região de interesse.
    """

    """
    mudar o morsaDict para ROIdict e adicionar os dados de step para linha neutra
    """ #to-do

    x1, y1, x2, y2 = _get_roi_coords(img.shape, roiDict)

    # Recorta a imagem
    if x2 > x1 and y2 > y1:
        img_recortada = img[y1:y2, x1:x2]
    else:
        # Fallback
        img_recortada = img

    return img_recortada

def gerar_preview(video_path, roiDict):
    """
    Gera um frame de preview com o retângulo ROI desenhado.
    Retorna a imagem RGB com o retângulo vermelho.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        return None

    # Converte para RGB para exibição correta no Tkinter/PIL e para poder desenhar colorido
    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Calcula coordenadas
    x1, y1, x2, y2 = _get_roi_coords(img_rgb.shape, roiDict)
    
    # Desenha retângulo vermelho (R, G, B) = (255, 0, 0)
    # Espessura 3 px
    cv2.rectangle(img_rgb, (x1, y1), (x2, y2), (255, 0, 0), 3)
    
    return img_rgb

def extrair_borda_superior(img_edges,
                           min_largura_viga=5,
                           passo_linhas=2):
    """
    img_edges: imagem binária (uint8) com bordas (0 ou 255) da viga
    """
    h, w = img_edges.shape
    pontos_borda = []

    # Percorre colunas (x) para viga horizontal
    for x in range(0, w, passo_linhas):
        coluna = img_edges[:, x]         # coluna x
        ys = np.where(coluna > 0)[0]     # índices das bordas (linhas)

        if ys.size < 1:
            continue  # nenhuma borda encontrada, ignora

        # Pega a primeira borda encontrada (índice 0)
        y_top = ys[0]

        pontos_borda.append([x, y_top])

    # Sem regressão linear, retorna apenas os pontos encontrados
    if len(pontos_borda) > 0:
        pontos_suavizados = np.array(pontos_borda, dtype=np.int32)
    else:
        pontos_suavizados = np.empty((0, 2), dtype=np.int32)

    # Visualização
    img_vis = cv2.cvtColor(img_edges, cv2.COLOR_GRAY2BGR)
    for x, y in pontos_suavizados:
        cv2.circle(img_vis, (int(x), int(y)), 1, (0, 0, 255), -1)

    return pontos_suavizados, img_vis


### Processamento principal OTIMIZADO (Memory-Based)

import data_extraction as de

def processar_frame(img, morsaDict=None):
    """
    Processa um único frame: Recorte -> Deteção de borda com precisão sub-pixel.
    Retorna: pontos_borda, imagem_visualizacao
    """ 
    
    if morsaDict:
        img = recortar_roi(img, morsaDict)

    # Extração de dados via sub-pixel EdgeDetector
    detector = de.EdgeDetector(step=2, grad_threshold=30.0)
    pontos, img_vis = detector.detect(img)
    
    return pontos, img_vis

def calcular_escala(video_path, escala_dict, pasta_saida=None):
    """
    Calcula os milímetros por pixel usando um frame do vídeo e o dicionário de calibração.
    escala_dict: {'x1': %, 'x2': %, 'y1': %, 'y2': %, 'h_mm': float}
    """
    if not escala_dict or 'h_mm' not in escala_dict:
        return 1.0

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return 1.0
        
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return 1.0
        
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    img_calib = recortar_roi(gray, escala_dict)
    img_vis = cv2.cvtColor(img_calib, cv2.COLOR_GRAY2BGR)
    
    # Aplicar gradiente vertical para achar as bordas
    blur = cv2.GaussianBlur(img_calib, (5, 5), 0)
    grad_y = cv2.Sobel(blur, cv2.CV_64F, 0, 1, ksize=3)
    grad_abs = np.abs(grad_y)
    
    h_img, w_img = img_calib.shape
    alturas_px = []
    
    step = 2
    grad_threshold = 30.0
    
    for x in range(0, w_img, step):
        col_grad = grad_abs[:, x]
        ys = np.where(col_grad > grad_threshold)[0]
        if len(ys) < 2:
            continue
            
        # Pega o primeiro pico (borda superior)
        y_top = -1
        for y in ys:
            if 0 < y < h_img - 1:
                if col_grad[y] >= col_grad[y-1] and col_grad[y] >= col_grad[y+1]:
                    y_top = y
                    break
                    
        # Pega o último pico (borda inferior)
        y_bot = -1
        for y in reversed(ys):
            if 0 < y < h_img - 1:
                if col_grad[y] >= col_grad[y-1] and col_grad[y] >= col_grad[y+1]:
                    y_bot = y
                    break
                    
        if y_top != -1 and y_bot != -1 and y_bot > y_top:
            alturas_px.append(float(y_bot - y_top))
            # Desenha a reta e os pontos na imagem de visualização
            cv2.line(img_vis, (x, y_top), (x, y_bot), (255, 0, 0), 1) # Linha azul
            cv2.circle(img_vis, (x, y_top), 1, (0, 255, 0), -1) # Ponto verde superior
            cv2.circle(img_vis, (x, y_bot), 1, (0, 0, 255), -1) # Ponto vermelho inferior
            
    if pasta_saida:
        caminho_img = os.path.join(pasta_saida, "verificacao_escala.jpg")
        smart_imwrite(caminho_img, img_vis)

    if len(alturas_px) > 0:
        altura_media_px = float(np.mean(alturas_px))
        escala_calculada = escala_dict['h_mm'] / altura_media_px
        print(f"Calibração de Escala: Altura em pixels ({altura_media_px:.2f}px) -> Fator {escala_calculada:.5f} mm/px")
        return escala_calculada
    else:
        print("Calibração de Escala falhou: Não foi possível detectar bordas sup/inf na área escolhida. Fator 1.0")
        return 1.0

def ler_vibracoes(caminho_video, pasta_saida, taxa_extracao, fps_video, ROI_dict=None, escala_dict=None):
    """
    Nova implementação de ler_vibracoes:
    - Lê o vídeo frame a frame.
    - Processa em memória (sem salvar frames intermediários).
    - Acumula dados físicos (TimeMatrix).
    - Salva CSV de dados e (opcionalmente) imagens de visualização.

    #to-do: 
    adicionar widget pra FPS manual, ou então tentar fazer com que o app leia o FPS. mas por garantia existir o manual.

    """
    # 1. Preparação
    if not caminho_video:
        raise ValueError("Caminho do vídeo não especificado.")
    
    limpar_pasta(pasta_saida)
    os.makedirs(pasta_saida, exist_ok=True)
    
    cap = cv2.VideoCapture(caminho_video)
    if not cap.isOpened():
        raise IOError(f"Não foi possível abrir o vídeo: {caminho_video}")

    if fps_video > 0: # checa a entrada do usuário na UI 
        fps = fps_video
    else:
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0: fps = 30.0 # Fallback 

    
    fator_escala = 1.0
    if escala_dict is not None:
        fator_escala = calcular_escala(caminho_video, escala_dict, pasta_saida)

    # Inicializa o acumulador de dados com a escala encontrada
    extractor = de.VibrationTimeSeries(fps=fps, scale_factor=fator_escala)

    messagebox.showinfo("Status", f"Iniciando processamento: {caminho_video}\n@ {fps:.2f} FPS\nEscala: {fator_escala:.4f} mm/px")
    
    frame_idx = 0
    saved_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Processar apenas a cada 'taxa_extracao' frames
        if frame_idx % taxa_extracao == 0:
            # Converter para grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Pipeline de extração
            pontos, img_vis = processar_frame(gray, ROI_dict)
            
            # Armazenar dados
            # pontos é um np.array [[x, y], ...], converter para lista de tuplas
            lista_pontos = [(float(p[0]), float(p[1])) for p in pontos]
            extractor.add_frame(frame_idx, lista_pontos)

            # Salvar imagem de visualização (opcional, mas bom para feedback visual)
            # Para não lotar o disco, podemos salvar apenas visualizações processadas
            nome_arquivo = f"proc_{saved_count:05d}.jpg"
            caminho_img = os.path.join(pasta_saida, nome_arquivo)
            smart_imwrite(caminho_img, img_vis)
            
            saved_count += 1    

        frame_idx += 1

    cap.release()

    # 2. Exportar Dados
    csv_path = os.path.join(pasta_saida, "dados_vibracao.csv")
    extractor.save_csv(csv_path)
    
    # 3. Gerar Gráficos e Salvar Frame de Maior Deflexão
    df = extractor.to_dataframe()
    try:
        import data_visualization as dv
        import structural_modal_analysis as sma
        
        # Encontra temporariamente o instante de maior deformação bruta apenas para a extração do JPG
        matriz_df = df.pivot(index='time_sec', columns='posicao_x_pixels', values='displacement_mm')
        matriz_df = matriz_df.interpolate(method='linear', axis=0).bfill(axis=0).ffill(axis=0).fillna(0.0)
        soma_deflexoes = matriz_df.abs().sum(axis=1)
        
        if not soma_deflexoes.empty:
            tempo_max = soma_deflexoes.idxmax()
            frame_max_idx = int(round(tempo_max * fps))
            
            cap_max = cv2.VideoCapture(caminho_video)
            cap_max.set(cv2.CAP_PROP_POS_FRAMES, frame_max_idx)
            ret_max, frame_raw = cap_max.read()
            if ret_max:
                gray_raw = cv2.cvtColor(frame_raw, cv2.COLOR_BGR2GRAY)
                pts_max, img_vis_max = processar_frame(gray_raw, ROI_dict)
                caminho_max = os.path.join(pasta_saida, "frame_maior_deflexao.jpg")
                smart_imwrite(caminho_max, img_vis_max)
                print(f"Frame de maior deflexão visual ({frame_max_idx} - {tempo_max:.3f}s) salvo separadamente.")
            cap_max.release()

        # O mathematical SVD computation happens internally inside these plots
        dv.plot_data_integrity(df, pasta_saida)
        dv.plot_natural_frequency(df, fps, pasta_saida)
        dv.plot_modal_shape_and_curvature(df, extractor.scale_factor, pasta_saida)
    except Exception as e:
        print(f"Erro ao gerar gráficos/salvar max frame: {e}")

    print(f"Processamento concluído. {saved_count} frames processados.")
    print(f"Dados salvos em: {csv_path}")

