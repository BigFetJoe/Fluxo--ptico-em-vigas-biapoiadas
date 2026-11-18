"""
Teste de fumaça headless: processa um vídeo de exemplo de ponta a ponta
(sem abrir a GUI) e apaga a saída ao final.

Uso (de dentro de códigos/app_final):
    python test_headless.py [caminho_do_video]
"""
import os
import sys
import shutil

# Garante que os módulos irmãos sejam importáveis independentemente do cwd
PASTA_APP = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PASTA_APP)

import tools as tll

# tools.ler_vibracoes chama messagebox.showinfo; no modo headless isso abriria
# uma janela Tk e travaria o teste. Substitui por print.
tll.messagebox.showinfo = lambda titulo, msg: print(f"[{titulo}] {msg}")

# Raiz do projeto = dois níveis acima de códigos/app_final
RAIZ_PROJETO = os.path.abspath(os.path.join(PASTA_APP, "..", ".."))
VIDEO_PADRAO = os.path.join(RAIZ_PROJETO, "vídeos exemplo para reunião", "1a freq.mp4")


def run_test(video_path=VIDEO_PADRAO):
    print("Iniciando teste headless...")

    output_path = os.path.join(PASTA_APP, "test_frames_saida")

    if not os.path.exists(video_path):
        print(f"ERRO: Vídeo não encontrado em {video_path}")
        return False

    # ROI em porcentagem (formato atual x1/x2/y1/y2): frame inteiro
    roi_dict = {'x1': 0, 'x2': 100, 'y1': 0, 'y2': 100}
    taxa = 5  # processa 1 a cada 5 frames, para o teste ser rápido

    sucesso = False
    try:
        print(f"Processando vídeo: {video_path}")
        print(f"Saída: {output_path}")

        tll.ler_vibracoes(video_path, output_path, taxa, fps_video=0, ROI_dict=roi_dict)

        esperados = ["dados_vibracao.csv", "matriz_deslocamentos.csv",
                     "integridade_dados.html", "frequencia_natural_FFT.html",
                     "forma_modal.html"]
        files = os.listdir(output_path)
        faltando = [f for f in esperados if f not in files]
        print(f"Arquivos gerados: {len(files)}")
        if faltando:
            print(f"FALHA: arquivos esperados ausentes: {faltando}")
        else:
            print("SUCESSO: todos os arquivos esperados foram gerados.")
            sucesso = True

    except Exception as e:
        print(f"ERRO DE EXECUÇÃO: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if os.path.exists(output_path):
            try:
                shutil.rmtree(output_path)
                print("Pasta de teste removida.")
            except Exception:
                print("Não foi possível remover pasta de teste.")
    return sucesso


if __name__ == "__main__":
    video = sys.argv[1] if len(sys.argv) > 1 else VIDEO_PADRAO
    sys.exit(0 if run_test(video) else 1)
