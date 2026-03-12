import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os

import tools as tll
import widgets as wdg

def main():
    janela = tk.Tk()
    janela.title("Extrator de dados de vibração")
    janela.geometry("700x250")

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
    entry_fps   = wdg.fps_video_entry(janela)   

    # Widgets de morsa -> recebem a função de callback de preview
    tem_morsa, x_entries, y_entries = wdg.entrada_ROI(janela, entry_video, cb_gerar_preview)
    tem_escala, x_entries_esc, y_entries_esc, entry_altura = wdg.entrada_escala(janela, entry_video, cb_gerar_preview)

    # --- Lógica de Processamento (Thread) ---
    def processar_em_background(video_path, taxa, fps_video, morsa_dict, escala_dict, pasta_saida):
        try:
            tll.ler_vibracoes(video_path, pasta_saida, taxa, fps_video, morsa_dict, escala_dict)
            # Sucesso
            janela.after(0, lambda: messagebox.showinfo("Concluído", f"Processamento finalizado!\nArquivos e gráficos salvos em:\n{pasta_saida}"))
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
        fps_str = entry_fps.get().strip() # Captura campo da UI

        if not v_path:
            messagebox.showerror("Erro", "Selecione um vídeo primeiro.")
            return

        try:
            taxa = int(t_str)
            if taxa < 1: raise ValueError
        except ValueError:
            messagebox.showwarning("Aviso", "Taxa inválida. Usando 1.")
            taxa = 1
            
        if not fps_str:
            fps_video = 0.0
        else:
            try:
                fps_video = float(fps_str)
            except ValueError:
                messagebox.showwarning("Aviso", "FPS inválido. Tentando calcular a partir do vídeo.")
                fps_video = 0.0

        morsaDict = None
        if tem_morsa.get():
            try:
                morsaDict = {
                    'x1': int(x_entries[0].get().strip()), 
                    'x2': int(x_entries[1].get().strip()),   
                    'y1': int(y_entries[0].get().strip()),     
                    'y2': int(y_entries[1].get().strip()),     
                }
            except ValueError:
                messagebox.showerror("Erro", "Verifique os parâmetros da morsa (devem ser números inteiros).")
                return

        escalaDict = None
        if tem_escala.get():
            try:
                escalaDict = {
                    'x1': int(x_entries_esc[0].get().strip()),
                    'x2': int(x_entries_esc[1].get().strip()),
                    'y1': int(y_entries_esc[0].get().strip()),
                    'y2': int(y_entries_esc[1].get().strip()),
                    'h_mm': float(entry_altura.get().strip())
                }
            except ValueError:
                messagebox.showerror("Erro", "Verifique os parâmetros de calibração de escala (coordenadas inteiras, altura numérica).")
                return

        # Caminho de saída (padrão ou perguntar? Por enquanto padrão, melhoria futura: perguntar)
        pasta_saida = os.path.join(os.getcwd(), "frames_saida")
        
        # 2. Iniciar Thread
        btn.config(state=tk.DISABLED, text="Processando...")
        
        t = threading.Thread(
            target=processar_em_background, 
            args=(v_path, taxa, fps_video, morsaDict, escalaDict, pasta_saida), 
            daemon=True 
        )
        t.start()

    # botão de extração
    btn = tk.Button(janela, text="Extrair dados", command=btn_vibr_click)
    btn.grid(row=10, column=0, columnspan=3, pady=10)

    janela.mainloop()

if __name__ == "__main__":
    main()