# Fluxo óptico em vigas biapoiadas — SHM por visão computacional

Aplicativo que extrai a vibração de uma viga a partir de vídeo de alta velocidade e estima
os parâmetros modais (frequência natural e forma modal) sem sensores de contato.

## Estrutura

- `app_final/` — o aplicativo (GUI Tkinter + pipeline de processamento).
- `requirements.txt` — dependências.
- Vídeos e resultados (`frames_saida/`) **não** são versionados: ficam na raiz do projeto, fora deste repositório.
- `teste*.py` e `extrair_frames.py` são scripts descartáveis, ignorados pelo git.

## Instalação

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

## Uso

Rodar de dentro de `app_final/` (os módulos se importam pelo nome e a saída vai para `./frames_saida`):

```
cd app_final
..\.venv\Scripts\python main.py
```

Teste de fumaça (processa `vídeos exemplo para reunião/1a freq.mp4` da raiz do projeto e apaga a saída):

```
cd app_final
..\.venv\Scripts\python test_headless.py [caminho_do_video]
```
