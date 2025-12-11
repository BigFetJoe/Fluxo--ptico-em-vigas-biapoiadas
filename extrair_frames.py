import cv2
import os
import tkinter as tk
from tkinter import filedialog, messagebox

def extrair_frames(caminho_video, pasta_saida, taxa_extracao=1):
    if not caminho_video or not pasta_saida:
        messagebox.showerror("Erro", "É necessário escolher o vídeo e a pasta de saída.")
        return

    if not os.path.exists(pasta_saida):
        try:
            os.makedirs(pasta_saida)
        except OSError as e:
            messagebox.showerror("Erro", f"Não foi possível criar a pasta:\n{pasta_saida}\n\nDetalhe: {e}")
            return

    video = cv2.VideoCapture(caminho_video)
    if not video.isOpened():
        messagebox.showerror("Erro", f"Não foi possível abrir o vídeo:\n{caminho_video}")
        return

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

def escolher_video():
    caminho = filedialog.askopenfilename(
        title='Selecione o arquivo de vídeo',
        filetypes=[('Vídeo', '*.mp4 *.avi *.mov *.mkv *.wmv *.m4v')]
    )
    entry_video.delete(0, tk.END)
    entry_video.insert(0, caminho)

def escolher_pasta():
    pasta = filedialog.askdirectory(title='Selecione a pasta de destino')
    entry_pasta.delete(0, tk.END)
    entry_pasta.insert(0, pasta)

def iniciar_extracao():
    caminho_video = entry_video.get().strip()
    pasta_saida = entry_pasta.get().strip()
    try:
        taxa = int(entry_taxa.get())
        if taxa < 1:
            raise ValueError
    except ValueError:
        messagebox.showwarning("Valor inválido", "Taxa de extração deve ser um inteiro >= 1.\nUsando 1.")
        taxa = 1
        entry_taxa.delete(0, tk.END)
        entry_taxa.insert(0, "1")
    extrair_frames(caminho_video, pasta_saida, taxa)

root = tk.Tk()
root.title("Extrator de Frames de Vídeo")
root.geometry("600x230")

tk.Label(root, text="Vídeo escolhido:").grid(row=0, column=0, padx=8, pady=10, sticky='w')
entry_video = tk.Entry(root, width=55)
entry_video.grid(row=0, column=1, padx=4)
btn_video = tk.Button(root, text="Selecionar vídeo", command=escolher_video)
btn_video.grid(row=0, column=2, padx=4)

tk.Label(root, text="Pasta de saída:").grid(row=1, column=0, padx=8, pady=10, sticky='w')
entry_pasta = tk.Entry(root, width=55)
entry_pasta.grid(row=1, column=1, padx=4)
btn_pasta = tk.Button(root, text="Selecionar pasta", command=escolher_pasta)
btn_pasta.grid(row=1, column=2, padx=4)

tk.Label(root, text="Taxa de extração (1 = todos):").grid(row=2, column=0, padx=8, pady=10, sticky='w')
entry_taxa = tk.Entry(root, width=10)
entry_taxa.insert(0, "1")
entry_taxa.grid(row=2, column=1, sticky='w')

btn_extrair = tk.Button(root, text="Extrair Frames",
                        command=iniciar_extracao,
                        bg="#2196F3", fg="#fff",
                        font=("Arial", 12, "bold"))
btn_extrair.grid(row=3, column=1, pady=20)

root.mainloop()
