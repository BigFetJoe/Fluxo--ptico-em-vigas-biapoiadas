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
        text="Existe morsa?",
        variable=tem_morsa
    )
    chk_morsa.grid(row=2, column=0, padx=10, pady=5, sticky="w")

    # frame de parâmetros (inicialmente escondido)
    frame_morsa1 = tk.LabelFrame(
        raiz,
        text="Parâmetros da morsa",
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
        text="Largura da morsa (% da imagem):"
    ).grid(row=0, column=0, padx=8, pady=10, sticky="w")

    entry_largura = tk.Entry(frame_morsa1, width=10)
    entry_largura.insert(0, "40")
    entry_largura.grid(row=0, column=1, sticky="w")

    tk.Label(
        frame_morsa1,
        text="Altura da morsa (% da imagem):"
    ).grid(row=1, column=0, padx=8, pady=10, sticky="w")

    entry_altura = tk.Entry(frame_morsa1, width=10)
    entry_altura.insert(0, "10")
    entry_altura.grid(row=1, column=1, sticky="w")

    tk.Label(
        frame_morsa1,
        text="(posição Y do centro da morsa \n em % da altura da imagem)"
    ).grid(row=2, column=0, columnspan=2, padx=8, pady=5, sticky="w")

    entry_posY = tk.Entry(frame_morsa1, width=10)
    entry_posY.insert(0, "90")
    entry_posY.grid(row=3, column=0)

    tk.Label(
        frame_morsa1,
        text="(posição X do centro da morsa \n em % da largura da imagem)"
    ).grid(row=2, column=1, padx=8, pady=5, sticky="w")

    entry_posX = tk.Entry(frame_morsa1, width=10)
    entry_posX.insert(0, "50")
    entry_posX.grid(row=3, column=1)

    lbl_preview = tk.Label(frame_morsa1, text="Preview")
    lbl_preview.grid(row=4, column=0, columnspan=2, pady=5)

    def atualizar_preview(*args):
        # Pega caminho do video
        video_path = entry_video.get()
        if not video_path:
            return

        # Pega valores dos entries
        try:
            lx = int(entry_largura.get())
            ly = int(entry_altura.get())
            py = int(entry_posY.get())
            px = int(entry_posX.get())
        except ValueError:
            return
        
        # Monta dict
        morsaDict = {
            'sizeX': lx,
            'sizeY': ly,
            'posY': py,
            'posX': px,
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
    entry_largura.bind('<KeyRelease>', atualizar_preview)
    entry_altura.bind('<KeyRelease>', atualizar_preview)
    entry_posY.bind('<KeyRelease>', atualizar_preview)
    entry_posX.bind('<KeyRelease>', atualizar_preview)
    entry_largura.bind('<FocusIn>', atualizar_preview)
    
    btn_upd = tk.Button(frame_morsa1, text="Atualizar Preview", command=atualizar_preview)
    btn_upd.grid(row=5, column=0, columnspan=2, pady=0)

    return tem_morsa, (entry_largura, entry_altura), (entry_posY, entry_posX)


