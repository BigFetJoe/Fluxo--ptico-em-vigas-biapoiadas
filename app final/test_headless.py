import sys
import os
import shutil

# Adiciona o diretório atual ao path para importar tools
sys.path.append(os.getcwd())

import tools as tll

def run_test():
    print("Iniciando teste headless...")
    
    # Caminhos
    base_dir = r"j:\Vscode\SHM_vigas_artigo"
    video_path = os.path.join(base_dir, "vídeos exemplo para reunião", "1a freq.mp4")
    output_path = os.path.join(os.getcwd(), "test_frames_saida")
    
    if not os.path.exists(video_path):
        print(f"ERRO: Vídeo não encontrado em {video_path}")
        return

    # Parâmetros
    morsaDict = {
        'posX': 50, 'posY': 50,
        'sizeX': 20, 'sizeY': 20
    }
    taxa = 500  # Alta taxa para processar poucos frames
    
    try:
        print(f"Processando vídeo: {video_path}")
        print(f"Saída: {output_path}")
        
        tll.ler_vibracoes(video_path, output_path, taxa, morsaDict)
        
        print("Processamento finalizado sem erros de execução.")
        
        # Verificar saída
        files = os.listdir(output_path)
        print(f"Arquivos gerados: {len(files)}")
        if len(files) > 0:
            print("SUCESSO: Arquivos foram gerados.")
            # Listar alguns
            print("Exemplos:", files[:5])
        else:
            print("FALHA: Nenhum arquivo gerado.")
            
    except Exception as e:
        print(f"ERRO DE EXECUÇÃO: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Limpeza
        if os.path.exists(output_path):
            try:
                shutil.rmtree(output_path)
                print("Pasta de teste removida.")
            except:
                print("Não foi possível remover pasta de teste.")

if __name__ == "__main__":
    run_test()
