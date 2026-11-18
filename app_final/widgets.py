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
    entry_taxa.grid(row=0, column=0, sticky='w')
    return entry_taxa


def corte_inicial_entry(roottk):
    """Campo para descartar os primeiros N segundos do vídeo (0 = sem corte)."""
    frame_corte = tk.LabelFrame(roottk, text="Cortar início (segundos):", padx=8, pady=8)
    frame_corte.grid(row=5, column=0, padx=10, pady=5, sticky='w')

    entry_corte = tk.Entry(frame_corte, width=10)
    entry_corte.insert(0, "0")
    entry_corte.grid(row=0, column=0, sticky='w')
    return entry_corte


#input de dados para a mascara da morsa.
def alternar_ROI(var, frame, root):
    """Mostra ou esconde o frame de parâmetros de morsa."""
    if var.get():
        frame.grid(row=1, column=1, columnspan=2, rowspan=3, padx=10, pady=5, sticky="nw")
        root.geometry("700x600")  # aumenta a janela para caber o preview
    else:
        frame.grid_remove()
        root.geometry("700x250")  # reduz a janela
    

def entrada_ROI(raiz, entry_video, cb_preview):
    """
    Cria o seletor de existência de ROI + frame de parâmetros.
    cb_preview: função(path_video, morsaDict) -> np.array (imagem cv2) ou None
    Retorna: tem_ROI (BooleanVar), (entry_largura, entry_altura), (entry_posY, entry_posX).
    """
    # variável de controle: existe ROI?
    tem_ROI = tk.BooleanVar(value=True)

    # checkbox de sim/não
    chk_ROI = tk.Checkbutton(
        raiz,
        text="Recortar imagem? (ROI)",
        variable=tem_ROI
    )
    chk_ROI.grid(row=2, column=0, padx=10, pady=5, sticky="w")

    # frame de parâmetros (inicialmente escondido)
    frame_ROI1 = tk.LabelFrame(
        raiz,
        text="Parâmetros de Recorte",
        padx=8,
        pady=8
    )
    # NÃO faz grid aqui; quem mostra/esconde é alternar_ROI

    # ligação da função de alternância (depois do frame existir)
    chk_ROI.configure(
        command=lambda: alternar_ROI(tem_ROI, frame_ROI1, raiz)
    )

    # widgets internos do frame
    tk.Label(
        frame_ROI1,
        text="X Inicial (%):"
    ).grid(row=0, column=0, padx=8, pady=5, sticky="w")

    entry_x1 = tk.Entry(frame_ROI1, width=10)
    entry_x1.insert(0, "0")
    entry_x1.grid(row=0, column=1, sticky="w")

    tk.Label(
        frame_ROI1,
        text="X Final (%):"
    ).grid(row=1, column=0, padx=8, pady=5, sticky="w")

    entry_x2 = tk.Entry(frame_ROI1, width=10)
    entry_x2.insert(0, "100")
    entry_x2.grid(row=1, column=1, sticky="w")

    tk.Label(
        frame_ROI1,
        text="Y Inicial (%):"
    ).grid(row=2, column=0, padx=8, pady=5, sticky="w")

    entry_y1 = tk.Entry(frame_ROI1, width=10)
    entry_y1.insert(0, "40")
    entry_y1.grid(row=2, column=1, sticky="w")

    tk.Label(
        frame_ROI1,
        text="Y Final (%):"
    ).grid(row=3, column=0, padx=8, pady=5, sticky="w")

    entry_y2 = tk.Entry(frame_ROI1, width=10)
    entry_y2.insert(0, "70")
    entry_y2.grid(row=3, column=1, sticky="w")

    lbl_preview = tk.Label(frame_ROI1, text="Preview")
    lbl_preview.grid(row=4, column=0, columnspan=2, pady=5)

    def atualizar_preview(*args):
        # Pega caminho do video
        video_paths_str = entry_video.get()
        if not video_paths_str:
            return
        video_path = video_paths_str.split(';')[0].strip()
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
        ROI_dict = {
            'x1': x1,
            'x2': x2,
            'y1': y1,
            'y2': y2,
        }

        # Chama callback injetado para obter a imagem processada
        img_show = cb_preview(video_path, ROI_dict)
        
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
    
    btn_upd = tk.Button(frame_ROI1, text="Atualizar Preview", command=atualizar_preview)
    btn_upd.grid(row=6, column=0, columnspan=2, pady=0)

    # Forçar a atualização visual inicial do frame
    alternar_ROI(tem_ROI, frame_ROI1, raiz)

    return tem_ROI, (entry_x1, entry_x2), (entry_y1, entry_y2)

def fps_video_entry(roottk):
    frame_fps = tk.LabelFrame(roottk, text="FPS do vídeo (vazio = auto):", padx=8, pady=8)
    frame_fps.grid(row=3, column=0, padx=10, pady=5, sticky='w')
    
    entry_fps = tk.Entry(frame_fps, width=10)
    entry_fps.insert(0, "440") # Deixe vazio para descobrir automaticamente
    entry_fps.grid(row=0, column=0, sticky='w')
    return entry_fps

def alternar_escala(var, frame, root):
    """Mostra ou esconde o frame de parâmetros de calibração de escala."""
    if var.get():
        frame.grid(row=1, column=3, columnspan=2, rowspan=4, padx=10, pady=5, sticky="nw")
        # Aumentamos mais a janela para caber dois previews se ambos estiverem abertos
        root.geometry("1100x650") 
    else:
        frame.grid_remove()
        root.geometry("700x250") # Retorna ao original (ou pelo menos esconde, o ideal seria avaliar se a Morsa está aberta, mas o Tkinter ajusta)

def entrada_escala(raiz, entry_video, cb_preview):
    """
    Cria o seletor de existência de calibração de cala + frame.
    Retorna: tem_escala (BooleanVar), (entries_X), (entries_Y), entry_altura.
    """
    tem_escala = tk.BooleanVar(value=True)

    chk_escala = tk.Checkbutton(
        raiz,
        text="Calibrar Escala (mm/px)",
        variable=tem_escala
    )
    chk_escala.grid(row=4, column=0, padx=10, pady=5, sticky="w")

    frame_escala = tk.LabelFrame(
        raiz,
        text="Recorte para Calibração (Viga)",
        padx=8,
        pady=8
    )

    chk_escala.configure(
        command=lambda: alternar_escala(tem_escala, frame_escala, raiz)
    )

    tk.Label(frame_escala, text="X Inicial (%):").grid(row=0, column=0, padx=8, pady=5, sticky="w")
    entry_x1_esc = tk.Entry(frame_escala, width=10)
    entry_x1_esc.insert(0, "0")
    entry_x1_esc.grid(row=0, column=1, sticky="w")

    tk.Label(frame_escala, text="X Final (%):").grid(row=1, column=0, padx=8, pady=5, sticky="w")
    entry_x2_esc = tk.Entry(frame_escala, width=10)
    entry_x2_esc.insert(0, "10")
    entry_x2_esc.grid(row=1, column=1, sticky="w")

    tk.Label(frame_escala, text="Y Inicial (%):").grid(row=2, column=0, padx=8, pady=5, sticky="w")
    entry_y1_esc = tk.Entry(frame_escala, width=10)
    entry_y1_esc.insert(0, "0")
    entry_y1_esc.grid(row=2, column=1, sticky="w")

    tk.Label(frame_escala, text="Y Final (%):").grid(row=3, column=0, padx=8, pady=5, sticky="w")
    entry_y2_esc = tk.Entry(frame_escala, width=10)
    entry_y2_esc.insert(0, "100")
    entry_y2_esc.grid(row=3, column=1, sticky="w")

    tk.Label(frame_escala, text="Altura da Viga (mm):").grid(row=4, column=0, padx=8, pady=5, sticky="w")
    entry_altura = tk.Entry(frame_escala, width=10)
    entry_altura.insert(0, "10.0")
    entry_altura.grid(row=4, column=1, sticky="w")

    lbl_preview = tk.Label(frame_escala, text="Preview Calibração")
    lbl_preview.grid(row=5, column=0, columnspan=2, pady=5)

    def atualizar_preview_escala(*args):
        video_paths_str = entry_video.get()
        if not video_paths_str:
            return
        video_path = video_paths_str.split(';')[0].strip()
        if not video_path:
            return

        try:
            x1 = int(entry_x1_esc.get())
            x2 = int(entry_x2_esc.get())
            y1 = int(entry_y1_esc.get())
            y2 = int(entry_y2_esc.get())
        except ValueError:
            return
        
        ROI_dict = {'x1': x1, 'x2': x2, 'y1': y1, 'y2': y2}
        img_show = cb_preview(video_path, ROI_dict)
        
        if img_show is None:
            return

        h, w = img_show.shape[:2]
        fator = 300 / w if w > 0 else 1
        novo_w = 300
        novo_h = int(h * fator)
        if novo_h > 250:
            fator = 250 / h
            novo_h = 250
            novo_w = int(w * fator)

        img_b = cv2.resize(img_show, (novo_w, novo_h))
        # PIL and ImageTk already globally imported in widgets.py
        im_pil = Image.fromarray(img_b)
        im_tk = ImageTk.PhotoImage(image=im_pil)
        
        lbl_preview.configure(image=im_tk, text="")
        lbl_preview.image = im_tk

    entry_x1_esc.bind('<KeyRelease>', atualizar_preview_escala)
    entry_x2_esc.bind('<KeyRelease>', atualizar_preview_escala)
    entry_y1_esc.bind('<KeyRelease>', atualizar_preview_escala)
    entry_y2_esc.bind('<KeyRelease>', atualizar_preview_escala)
    
    btn_upd = tk.Button(frame_escala, text="Atualizar Preview", command=atualizar_preview_escala)
    btn_upd.grid(row=6, column=0, columnspan=2, pady=0)

    # Forçar a atualização visual inicial do frame
    alternar_escala(tem_escala, frame_escala, raiz)

    return tem_escala, (entry_x1_esc, entry_x2_esc), (entry_y1_esc, entry_y2_esc), entry_altura
