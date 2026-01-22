import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os

import tools as tll
import widgets as wdg

def main():
    janela = tk.Tk()
    janela.title("Extrator de dados de vibração")
    janela.geometry("700x150")

    # --- Callbacks para UI ---
    def cmd_selecionar_video(entry_widget):
        caminho = filedialog.askopenfilename(
            title='Selecione o arquivo de vídeo',
            filetypes=[('Vídeo', '*.mp4 *.avi *.mov *.mkv *.wmv *.m4v')]
        )
        if caminho:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, caminho)

    def cb_gerar_preview(video_path, morsa_dict):
        """Callback que widgets usa para pedir um preview."""
        return tll.gerar_preview(video_path, morsa_dict)

    # --- Widgets ---
    # Injeção de dependências: passamos as funções de comando
    entry_video = wdg.escolha_video(janela, cmd_selecionar_video)
    entry_taxa  = wdg.taxa_extracao_entry(janela)

    # Widgets de morsa -> recebem a função de callback de preview
    tem_morsa, tamanho_morsa, pos_morsa = wdg.entrada_morsa(janela, entry_video, cb_gerar_preview)

    # --- Lógica de Processamento (Thread) ---
    def processar_em_background(video_path, taxa, morsa_dict, pasta_saida):
        try:
            tll.ler_vibracoes(video_path, pasta_saida, taxa, morsa_dict)
            # Sucesso
            janela.after(0, lambda: messagebox.showinfo("Concluído", f"Processamento finalizado!\nArquivos em: {pasta_saida}"))
        except Exception as e:
            # Erro
            janela.after(0, lambda: messagebox.showerror("Erro de Processamento", f"Ocorreu um erro:\n{e}"))
        finally:
            # Reabilitar botão (exemplo)
            janela.after(0, lambda: btn.config(state=tk.NORMAL, text="Extrair dados"))

    def btn_vibr_click():
        # 1. Coleta e Validação de inputs (Na Thread UI)
        v_path = entry_video.get().strip()
        t_str = entry_taxa.get().strip()

        if not v_path:
            messagebox.showerror("Erro", "Selecione um vídeo primeiro.")
            return

        try:
            taxa = int(t_str)
            if taxa < 1: raise ValueError
        except ValueError:
            messagebox.showwarning("Aviso", "Taxa inválida. Usando 1.")
            taxa = 1

        morsaDict = None
        if tem_morsa.get():
            try:
                morsaDict = {
                    'sizeX': int(tamanho_morsa[0].get().strip()), 
                    'sizeY': int(tamanho_morsa[1].get().strip()),   
                    'posY': int(pos_morsa[0].get().strip()),     
                    'posX': int(pos_morsa[1].get().strip()),     
                }
            except ValueError:
                messagebox.showerror("Erro", "Verifique os parâmetros da morsa (devem ser números inteiros).")
                return

        # Caminho de saída (padrão ou perguntar? Por enquanto padrão, melhoria futura: perguntar)
        pasta_saida = os.path.join(os.getcwd(), "frames_saida")
        
        # 2. Iniciar Thread
        btn.config(state=tk.DISABLED, text="Processando...")
        
        t = threading.Thread(
            target=processar_em_background, 
            args=(v_path, taxa, morsaDict, pasta_saida),
            daemon=True 
        )
        t.start()

    # botão de extração
    btn = tk.Button(janela, text="Extrair dados", command=btn_vibr_click)
    btn.grid(row=10, column=0, columnspan=3, pady=10)

    janela.mainloop()

if __name__ == "__main__":
    main()