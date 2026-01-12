import tkinter as tk

from sympy import root
import tools as tll
import widgets as wdg
import os

def main():
    janela = tk.Tk()
    janela.title("Extrator de dados de vibração")
    janela.geometry("700x150")

    # widgets de seleção de vídeo e taxa de extração
    entry_video = wdg.escolha_video(janela)
    entry_taxa  = wdg.taxa_extracao_entry(janela)

    # widgets de entrada da morsa (seletor + parâmetros)
    tem_morsa, tamanho_morsa, pos_morsa = wdg.entrada_morsa(janela)

    # callback do botão 'Extrair Frames'
    def btn_vibr():
        if tem_morsa.get():
            morsaDict = {
                'sizeX': int(tamanho_morsa[0].get().strip()),  # tamanho em %
                'sizeY': int(tamanho_morsa[1].get().strip()),   # tamanho em %
                'posY': int(pos_morsa[0].get().strip()),     # posição Y do centro da morsa em %
                'posX': int(pos_morsa[1].get().strip()),     # posição X do centro da morsa em %
            }
        else:
            morsaDict = None  # ou {}, se preferir

        tll.ler_vibracoes(entry_video, entry_taxa, morsaDict)

    # botão de extração
    btn = tk.Button(janela, text="Extrair dados", command=btn_vibr)
    btn.grid(row=10, column=0, columnspan=3, pady=10)

    janela.mainloop()

if __name__ == "__main__":
    main()