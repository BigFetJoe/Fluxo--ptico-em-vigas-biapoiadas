import tkinter as tk
from tkinter import filedialog
import tools as tll


def escolha_video(roottk):
    tk.Label(roottk, text="Vídeo escolhido:").grid(row=0, column=0, padx=8, pady=10, sticky='w')
    entry_video = tk.Entry(roottk, width=55)
    entry_video.grid(row=0, column=1, padx=4)
    btn_video = tk.Button(roottk, text="Selecionar vídeo", command=lambda: tll.escolher_video(entry_video))
    btn_video.grid(row=0, column=2, padx=4)
    return entry_video

def taxa_extracao_entry(roottk):
    tk.Label(roottk, text="Taxa de extração (1 = todos):").grid(row=1, column=0, padx=8, pady=10, sticky='w')
    entry_taxa = tk.Entry(roottk, width=10)
    entry_taxa.insert(0, "1")
    entry_taxa.grid(row=1, column=1, sticky='w')
    return entry_taxa

#botão para extração de dados de vibração
def btn_vbr(roottk, entry_video, entry_taxa):
    btn_extrair = tk.Button(roottk, text="Extrair Frames",
                            command=lambda: tll.btn_vibr(entry_video, entry_taxa),
                            bg="#2F85CB", fg="#fff",
                            font=("Arial", 12, "bold"))

    btn_extrair.grid(row=2, column=1, pady=20)
    pass