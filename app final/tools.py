import cv2
import os
import tkinter as tk
from tkinter import filedialog, messagebox
import datetime

### extração de frames do vídeo

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


def btn_canny(entry_video, entry_taxa):
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

    extrair_frames(caminho_video, pasta_frames, taxa)

    for arquivo in os.listdir(pasta_frames):
        if arquivo.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
            caminho_imagem = os.path.join(pasta_frames, arquivo)
            img = cv2.imread(caminho_imagem, cv2.IMREAD_GRAYSCALE)
            blur = cv2.GaussianBlur(img, (3, 3), 0)

            # Aplica Canny
            edges = cv2.Canny(blur, 100, 200)

            # Salva a imagem resultante
            nome_saida = os.path.join(pasta_frames, f"canny_{arquivo}")
            cv2.imwrite(nome_saida, edges)  
    
    return None