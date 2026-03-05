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

def linha_neutra(img_edges,
                 min_largura_viga=5,
                 passo_linhas=2):
    """
    img_edges: imagem binária (uint8) com bordas (0 ou 255) da viga
    """
    h, w = img_edges.shape
    pontos_neutros = []

    # Percorre colunas (x) para viga horizontal
    for x in range(0, w, passo_linhas):
        coluna = img_edges[:, x]         # coluna x
        ys = np.where(coluna > 0)[0]     # índices das bordas (linhas)

        if ys.size < 2:
            continue  # menos de 2 bordas, ignora

        # Pega a primeira e a segunda bordas encontradas (índices 0 e 1)
        y_top = ys[0]
        y_bottom = ys[1]

        if (y_bottom - y_top) < min_largura_viga:
            continue  # muito próximos, ignora

        y_centro = (y_top + y_bottom) / 2.0
        pontos_neutros.append([x, y_centro])

    # Sem regressão linear, retorna apenas os pontos encontrados
    if len(pontos_neutros) > 0:
        pontos_suavizados = np.array(pontos_neutros, dtype=np.int32)
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
    Processa um único frame: Recorte -> Blur -> Canny -> Linha Neutra.
    Retorna: pontos_neutros, imagem_visualizacao
    """ 
    
    """
    Será mudado depois para deteção subpixel!!! 
    """ #to-do
    
    if morsaDict:
        img = recortar_roi(img, morsaDict)

    # Pré-processamento
    blur = cv2.GaussianBlur(img, (5, 5), 0)
    edges = cv2.Canny(blur, 10, 150)

    # Extração de dados
    pontos, img_vis = linha_neutra(edges)
    
    return pontos, img_vis

def ler_vibracoes(caminho_video, pasta_saida, taxa_extracao, fps_video, ROI_dict=None):
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

    
    # Inicializa o acumulador de dados
    extractor = de.VibrationTimeSeries(fps=fps, scale_factor=1.0)

    messagebox.showinfo("Status", f"Iniciando processamento: {caminho_video}\n@ {fps:.2f} FPS")
    
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
    
    # 3. Gerar Gráficos
    df = extractor.to_dataframe()
    try:
        import data_visualization as dv
        dv.plot_data_integrity(df, pasta_saida)
        dv.plot_natural_frequency(df, fps, pasta_saida)
        dv.plot_modal_shape_and_curvature(df, pasta_saida)
    except Exception as e:
        print(f"Erro ao gerar gráficos: {e}")

    print(f"Processamento concluído. {saved_count} frames processados.")
    print(f"Dados salvos em: {csv_path}")

