import cv2
import os
import numpy as np
import shutil

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


### Processamento principal

def extrair_frames(caminho_video, pasta_saida, taxa_extracao=1):
    if not caminho_video:
        raise ValueError("Caminho do vídeo não especificado.")
     
    if not os.path.exists(pasta_saida):
        os.makedirs(pasta_saida, exist_ok=True) # garante criação

    video = cv2.VideoCapture(caminho_video)
    if not video.isOpened():
        raise IOError(f"Não foi possível abrir o vídeo: {caminho_video}")

    salvo = 0
    cont = 0
    while True:
        ret, frame = video.read()
        if not ret:
            break

        if cont % taxa_extracao == 0:
            nome_frame = os.path.join(pasta_saida, f"frame_{salvo:05d}.png")
            
            # USO de smart_imwrite
            ok = smart_imwrite(nome_frame, frame)
            
            if not ok:
                video.release()
                raise IOError(f"Falha ao salvar frame: {nome_frame}")
            salvo += 1
        cont += 1

    video.release()
    print(f"Extração concluída: {salvo} frames em {pasta_saida}")
    return salvo

def cannyLoop(pasta_frames, morsaDict=None):
    for arquivo in os.listdir(pasta_frames):
        if arquivo.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
            caminho_imagem = os.path.join(pasta_frames, arquivo)
            
            # USO de smart_imread
            img = smart_imread(caminho_imagem, cv2.IMREAD_GRAYSCALE)
            
            if img is None: continue

            if morsaDict:
                img = recortar_roi(img, morsaDict)

            blur = cv2.GaussianBlur(img, (5, 5), 0)
            
            # Aplica Canny
            edges = cv2.Canny(blur, 70, 200)

            # Salva a imagem resultante
            nome_saida = os.path.join(pasta_frames, f"canny_{arquivo}")
            
            # USO de smart_imwrite
            smart_imwrite(nome_saida, edges)
            
            try:
                os.remove(caminho_imagem)  # Remove a imagem original
            except OSError:
                pass
    print("Canny aplicado.")

def linha_neutra_loop(pasta_frames):
    for arquivo in os.listdir(pasta_frames):
        if arquivo.lower().startswith('canny_') and arquivo.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
            caminho_imagem = os.path.join(pasta_frames, arquivo)
            
            # USO de smart_imread
            img_edges = smart_imread(caminho_imagem, cv2.IMREAD_GRAYSCALE)
            
            if img_edges is None: continue

            pontos_neutros, img_vis = linha_neutra(img_edges)

            # Salva a imagem de visualização
            nome_saida = os.path.join(pasta_frames, f"linha_neutra_{arquivo}")
            
            # USO de smart_imwrite
            smart_imwrite(nome_saida, img_vis)
            
            try:
                os.remove(caminho_imagem)  # Remove a imagem de bordas
            except OSError:
                pass
    print("Linha neutra extraída.")


def ler_vibracoes(caminho_video, pasta_saida, taxa_extracao, morsaDict=None):
    """
    Função principal que orquestra o processamento.
    Agora aceita pasta_saida explicitamente e não bloqueia UI com imshows.
    """
    # 1. Limpeza e Preparação
    limpar_pasta(pasta_saida)
    os.makedirs(pasta_saida, exist_ok=True)

    # 2. Extração
    extrair_frames(caminho_video, pasta_saida, taxa_extracao)

    # 3. Canny
    cannyLoop(pasta_saida, morsaDict)

    # 4. Linha Neutra (Optical Flow simulado / preparo)
    linha_neutra_loop(pasta_saida)

