import cv2
import os
import tkinter as tk
from tkinter import filedialog, messagebox
import datetime
from networkx import edges
import numpy as np

### extração de frames do vídeo
def escolher_video(entry_video):
    caminho = filedialog.askopenfilename(
        title='Selecione o arquivo de vídeo',
        filetypes=[('Vídeo', '*.mp4 *.avi *.mov *.mkv *.wmv *.m4v')]
    )
    entry_video.delete(0, tk.END)
    entry_video.insert(0, caminho)

def escolher_pasta(entry_pasta):
    pasta = filedialog.askdirectory(title='Selecione a pasta de destino')
    entry_pasta.delete(0, tk.END)
    entry_pasta.insert(0, pasta)

def iniciar_extracao_frames(entry_video, entry_taxa):
    caminho_video = entry_video.get().strip()
    try:
        taxa = int(entry_taxa.get())
        if taxa < 1:
            raise ValueError
        
    except ValueError:
        messagebox.showwarning("Valor inválido", "Taxa de extração deve ser um inteiro >= 1.\nUsando 1.")
        taxa = 1
        entry_taxa.delete(0, tk.END)
        entry_taxa.insert(0, "1")
    extrair_frames(caminho_video, taxa)

#função de limpesa
def limpar_pasta(pasta):
    if os.path.exists(pasta):
        for arquivo in os.listdir(pasta):
            caminho_arquivo = os.path.join(pasta, arquivo)
            try:
                if os.path.isfile(caminho_arquivo) or os.path.islink(caminho_arquivo):
                    os.unlink(caminho_arquivo)
                elif os.path.isdir(caminho_arquivo):
                    os.rmdir(caminho_arquivo)
            except Exception as e:
                print(f"Erro ao remover {caminho_arquivo}: {e}")
    else:
        print(f"A pasta {pasta} não existe.")

### Funções auxiliares para processamento de vídeo e imagens
def mascara_morsa(img, MorsaDict):
    """
    img: imagem em escala de cinza (h, w)
    center_pct: (cx_pct, cy_pct) em %, ex: (50, 80)
    size_pct: (w_pct, h_pct) em %, ex: (20, 30)
    """
    h, w = img.shape

    cx_pct, cy_pct = MorsaDict['posX'], MorsaDict['posY']
    w_pct,  h_pct  = MorsaDict['sizeX'], MorsaDict['sizeY']

    cy_pct = 100 - cy_pct  # inverter Y para coordenadas de imagem

    # centro em pixels
    cx = (cx_pct / 100.0) * w
    cy = (cy_pct / 100.0) * h

    # metade da largura/altura em pixels
    half_w = (w_pct / 100.0) * w / 2.0
    half_h = (h_pct / 100.0) * h / 2.0

    # coordenadas do retângulo
    x1 = int(cx - half_w)
    x2 = int(cx + half_w)
    y1 = int(cy - half_h)
    y2 = int(cy + half_h)

    # garantir que fiquem dentro da imagem
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(w, x2)
    y2 = min(h, y2)

    # cria máscara branca
    mask = np.ones((h, w), dtype=np.uint8) * 255

    # zera região da morsa
    mask[y1:y2, x1:x2] = 0

    # aplica máscara
    img_mascarada = cv2.bitwise_and(img, img, mask=mask)
    return img_mascarada

def linha_neutra(img_edges,
                 min_largura_viga=5,
                 passo_linhas=2):
    """
    img_edges: imagem binária (uint8) com bordas (0 ou 255) da viga
    min_largura_viga: largura mínima em pixels para aceitar um par de bordas
    passo_linhas: pular linhas para acelerar (1 = todas as linhas)
    """
    h, w = img_edges.shape
    pontos_neutros = []

    for y in range(0, h, passo_linhas):
        linha = img_edges[y, :]          # linha y
        xs = np.where(linha > 0)[0]      # índices das bordas

        if xs.size < 2:
            continue  # menos de 2 bordas, ignora

        x_esq = xs.min()
        x_dir = xs.max()

        if (x_dir - x_esq) < min_largura_viga:
            continue  # ruído, não parece ser a viga

        x_centro = (x_esq + x_dir) / 2.0
        pontos_neutros.append([x_centro, y])

    pontos_neutros = np.array(pontos_neutros, dtype=np.float32)

    # Opcional: ajusta uma reta x(y) = a*y + b para suavizar
    if len(pontos_neutros) >= 2:
        ys = pontos_neutros[:, 1]
        xs = pontos_neutros[:, 0]
        A = np.vstack([ys, np.ones_like(ys)]).T
        a, b = np.linalg.lstsq(A, xs, rcond=None)[0]
        xs_fit = a * ys + b
        pontos_suavizados = np.vstack([xs_fit, ys]).T.astype(np.int32)
    else:
        pontos_suavizados = pontos_neutros.astype(np.int32)

    # Visualização
    img_vis = cv2.cvtColor(img_edges, cv2.COLOR_GRAY2BGR)
    for x, y in pontos_suavizados:
        cv2.circle(img_vis, (int(x), int(y)), 1, (0, 0, 255), -1)

    return pontos_suavizados, img_vis


### funções principais para o bottão de extração de dados de vibração
def extrair_frames(caminho_video, pasta_saida, taxa_extracao=1):
    if not caminho_video:
        messagebox.showerror("Erro", "É necessário escolher um vídeo.")
     
    if not os.path.exists(pasta_saida):
        try:
            os.makedirs(pasta_saida)
        except OSError as e:
            messagebox.showerror("Erro", f"Não foi possível criar a pasta:\n{pasta_saida}\n\nDetalhe: {e}")
            

    video = cv2.VideoCapture(caminho_video)
    if not video.isOpened():
        messagebox.showerror("Erro", f"Não foi possível abrir o vídeo:\n{caminho_video}")
        

    total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = video.get(cv2.CAP_PROP_FPS)
    largura = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    altura = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))

    info = f"Vídeo aberto com sucesso.\nFrames: {total_frames}\nFPS: {fps:.2f}\nResolução: {largura}x{altura}"
    messagebox.showinfo("Informações do vídeo", info)

    cont = 0
    salvo = 0
    while True:
        ret, frame = video.read()
        if not ret:
            break

        if cont % taxa_extracao == 0:
            nome_frame = os.path.join(pasta_saida, f"frame_{salvo:05d}.png")
            ok = cv2.imwrite(nome_frame, frame)
            if not ok:
                messagebox.showerror("Erro ao salvar",
                                     f"Não foi possível salvar o frame:\n{nome_frame}\n"
                                     f"Verifique permissões e espaço em disco.")
                video.release()
                return 
            salvo += 1
        cont += 1

    video.release()
    messagebox.showinfo("Concluído", f"{salvo} frames salvos em:\n{pasta_saida}")
    return 

def cannyLoop(pasta_frames, morsaDict=None):
    for arquivo in os.listdir(pasta_frames):
        if arquivo.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
            caminho_imagem = os.path.join(pasta_frames, arquivo)
            img = cv2.imread(caminho_imagem, cv2.IMREAD_GRAYSCALE)
            blur = cv2.GaussianBlur(img, (5, 5), 0)
           
            # Aplica Canny
            edges = cv2.Canny(blur, 100, 240)
            
            #aplica máscara da morsa aqui se necessário
            if morsaDict:
                edges = mascara_morsa(edges, morsaDict)

            # Salva a imagem resultante
            nome_saida = os.path.join(pasta_frames, f"canny_{arquivo}")
            cv2.imwrite(nome_saida, edges)
            os.remove(caminho_imagem)  # Remove a imagem original
    messagebox.showinfo("Concluído", f"Detecção de bordas aplicada a todos os frames.\nResultados salvos em:\n{pasta_frames}")

def linha_neutra_loop(pasta_frames):
    for arquivo in os.listdir(pasta_frames):
        if arquivo.lower().startswith('canny_') and arquivo.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
            caminho_imagem = os.path.join(pasta_frames, arquivo)
            img_edges = cv2.imread(caminho_imagem, cv2.IMREAD_GRAYSCALE)

            pontos_neutros, img_vis = linha_neutra(img_edges)

            # Salva a imagem de visualização
            nome_saida = os.path.join(pasta_frames, f"linha_neutra_{arquivo}")
            cv2.imwrite(nome_saida, img_vis)
            os.remove(caminho_imagem)  # Remove a imagem de bordas
    messagebox.showinfo("Concluído", f"Linha neutra extraída de todos os frames.\nResultados salvos em:\n{pasta_frames}")



## função do botão de extração de dados de vibração com Canny
def ler_vibracoes(entry_video, entry_taxa, morsaDict=None):
    #extração de frames
    caminho_video = entry_video.get().strip()
    try:
        taxa = int(entry_taxa.get())
        if taxa < 1:
            raise ValueError
        
    except ValueError:
        messagebox.showwarning("Valor inválido", "Taxa de extração deve ser um inteiro >= 1.\nUsando 1.")
        taxa = 1
        entry_taxa.delete(0, tk.END)
        entry_taxa.insert(0, "1")
    
    #geração da pasta de frames 
    pasta_frames = os.path.join(os.getcwd(), "frames_saida")

    limpar_pasta(pasta_frames)
    
    if not os.path.exists(pasta_frames):
        raise OSError(f"Não foi possível criar a pasta:\n{pasta_frames}")

    extrair_frames(caminho_video, pasta_frames, taxa)

    # aplicação do Canny em todos os frames
    cannyLoop(pasta_frames, morsaDict)

    cv2.imshow("Teste1", cv2.imread(os.path.join(pasta_frames, os.listdir(pasta_frames)[0])))

    # TESTE -_-_-_-_-_-_-_-_
    
    cv2.imshow("Teste2", cv2.imread(os.path.join(pasta_frames, os.listdir(pasta_frames)[0])))
    
    # Identificação de pontos de interesse para optical flow. (caso seja escolhido pontos esparsos)
    linha_neutra_loop(pasta_frames)

    #extração do optical flow

    #teste 
    cv2.imshow("Teste3", cv2.imread(os.path.join(pasta_frames, os.listdir(pasta_frames)[0])))
    cv2.waitKey(0)  
    cv2.destroyAllWindows()
