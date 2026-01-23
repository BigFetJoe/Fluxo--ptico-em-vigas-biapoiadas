import tkinter as tk
from tkinter import filedialog
import cv2
from PIL import Image, ImageTk


#widget para escolha de vídeo
def escolha_video(roottk, cmd_selecionar):
    tk.Label(roottk, text="Vídeo escolhido:").grid(row=0, column=0, padx=8, pady=10)
    
    entry_video = tk.Entry(roottk, width=65)
    entry_video.grid(row=0, column=1, padx=4)
    
    btn_video = tk.Button(roottk, text="Selecionar vídeo", command=lambda: cmd_selecionar(entry_video))
    btn_video.grid(row=0, column=2, padx=4)
    return entry_video

def taxa_extracao_entry(roottk):
    frame_extracao = tk.LabelFrame(roottk, text="Taxa de extração (1 = todos):", padx=8, pady=8)
    frame_extracao.grid(row=1, column=0, padx=10, pady=5, sticky='w')
    
    entry_taxa = tk.Entry(frame_extracao, width=10)
    entry_taxa.insert(0, "1")
    entry_taxa.grid(row=2, column=1, sticky='w')
    return entry_taxa


#input de dados para a mascara da morsa.
def alternar_morsa(var, frame, root):
    """Mostra ou esconde o frame de parâmetros de morsa."""
    if var.get():
        frame.grid(row=1, column=1, columnspan=2, rowspan=2, padx=10, pady=5, sticky="nw")
        root.geometry("700x600")  # aumenta a janela para caber o preview
    else:
        frame.grid_remove()
        root.geometry("700x150")  # reduz a janela
    

def entrada_morsa(raiz, entry_video, cb_preview):
    """
    Cria o seletor de existência de morsa + frame de parâmetros.
    cb_preview: função(path_video, morsaDict) -> np.array (imagem cv2) ou None
    Retorna: tem_morsa (BooleanVar), (entry_largura, entry_altura), (entry_posY, entry_posX).
    """
    # variável de controle: existe morsa?
    tem_morsa = tk.BooleanVar(value=False)

    # checkbox de sim/não
    chk_morsa = tk.Checkbutton(
        raiz,
        text="Recortar imagem? (ROI)",
        variable=tem_morsa
    )
    chk_morsa.grid(row=2, column=0, padx=10, pady=5, sticky="w")

    # frame de parâmetros (inicialmente escondido)
    frame_morsa1 = tk.LabelFrame(
        raiz,
        text="Parâmetros de Recorte",
        padx=8,
        pady=8
    )
    # NÃO faz grid aqui; quem mostra/esconde é alternar_morsa

    # ligação da função de alternância (depois do frame existir)
    chk_morsa.configure(
        command=lambda: alternar_morsa(tem_morsa, frame_morsa1, raiz)
    )

    # widgets internos do frame
    tk.Label(
        frame_morsa1,
        text="X Inicial (%):"
    ).grid(row=0, column=0, padx=8, pady=5, sticky="w")

    entry_x1 = tk.Entry(frame_morsa1, width=10)
    entry_x1.insert(0, "0")
    entry_x1.grid(row=0, column=1, sticky="w")

    tk.Label(
        frame_morsa1,
        text="X Final (%):"
    ).grid(row=1, column=0, padx=8, pady=5, sticky="w")

    entry_x2 = tk.Entry(frame_morsa1, width=10)
    entry_x2.insert(0, "100")
    entry_x2.grid(row=1, column=1, sticky="w")

    tk.Label(
        frame_morsa1,
        text="Y Inicial (%):"
    ).grid(row=2, column=0, padx=8, pady=5, sticky="w")

    entry_y1 = tk.Entry(frame_morsa1, width=10)
    entry_y1.insert(0, "0")
    entry_y1.grid(row=2, column=1, sticky="w")

    tk.Label(
        frame_morsa1,
        text="Y Final (%):"
    ).grid(row=3, column=0, padx=8, pady=5, sticky="w")

    entry_y2 = tk.Entry(frame_morsa1, width=10)
    entry_y2.insert(0, "100")
    entry_y2.grid(row=3, column=1, sticky="w")

    lbl_preview = tk.Label(frame_morsa1, text="Preview")
    lbl_preview.grid(row=4, column=0, columnspan=2, pady=5)

    def atualizar_preview(*args):
        # Pega caminho do video
        video_path = entry_video.get()
        if not video_path:
            return

        # Pega valores dos entries
        try:
            x1 = int(entry_x1.get())
            x2 = int(entry_x2.get())
            y1 = int(entry_y1.get())
            y2 = int(entry_y2.get())
        except ValueError:
            return
        
        # Monta dict
        morsaDict = {
            'x1': x1,
            'x2': x2,
            'y1': y1,
            'y2': y2,
        }

        # Chama callback injetado para obter a imagem processada
        img_show = cb_preview(video_path, morsaDict)
        
        if img_show is None:
            return

        # Resize para caber no label
        h, w = img_show.shape[:2]
        fator = 300 / w if w > 0 else 1
        novo_w = 300
        novo_h = int(h * fator)
        if novo_h > 250: # limite altura tambem
            fator = 250 / h
            novo_h = 250
            novo_w = int(w * fator)

        img_b = cv2.resize(img_show, (novo_w, novo_h))
        
        # Converte para ImageTk
        im_pil = Image.fromarray(img_b)
        im_tk = ImageTk.PhotoImage(image=im_pil)
        
        lbl_preview.configure(image=im_tk, text="")
        lbl_preview.image = im_tk # manter referencia

    # Binds
    entry_x1.bind('<KeyRelease>', atualizar_preview)
    entry_x2.bind('<KeyRelease>', atualizar_preview)
    entry_y1.bind('<KeyRelease>', atualizar_preview)
    entry_y2.bind('<KeyRelease>', atualizar_preview)
    
    btn_upd = tk.Button(frame_morsa1, text="Atualizar Preview", command=atualizar_preview)
    btn_upd.grid(row=6, column=0, columnspan=2, pady=0)

    return tem_morsa, (entry_x1, entry_x2), (entry_y1, entry_y2)


