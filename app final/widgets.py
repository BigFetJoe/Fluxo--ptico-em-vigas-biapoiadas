import tkinter as tk
from tkinter import filedialog
import tools as tll


#widget para escolha de vídeo
def escolha_video(roottk):
    tk.Label(roottk, text="Vídeo escolhido:").grid(row=0, column=0, padx=8, pady=10)
    
    entry_video = tk.Entry(roottk, width=65)
    entry_video.grid(row=0, column=1, padx=4)
    
    btn_video = tk.Button(roottk, text="Selecionar vídeo", command=lambda: tll.escolher_video(entry_video))
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
        root.geometry("700x300")  # aumenta a janela
    else:
        frame.grid_remove()
        root.geometry("700x150")  # reduz a janela
    

def entrada_morsa(raiz):
    """
    Cria o seletor de existência de morsa + frame de parâmetros.
    Retorna: entry_largura, entry_altura, tem_morsa (BooleanVar).
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

    return tem_morsa, (entry_largura, entry_altura), (entry_posY, entry_posX)


