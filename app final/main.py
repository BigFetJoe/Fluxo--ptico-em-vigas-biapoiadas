import tkinter as tk
import tools as tll
import widgets as wdg
import os

def main():
    #janela
    janela = tk.Tk()
    janela.title("Extrator de dados de vibração")
    janela.geometry("700x150")
    
    #widgets de seleção de vídeo e taxa de extração
    entry_video = wdg.escolha_video(janela)
    entry_taxa = wdg.taxa_extracao_entry(janela)
    wdg.btn_vbr(janela, entry_video, entry_taxa)

    #widgets de extração de dados de vibração





    janela.mainloop()

if __name__ == "__main__": 
    main()