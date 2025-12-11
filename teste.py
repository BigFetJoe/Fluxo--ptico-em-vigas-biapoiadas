from tkinter import filedialog
import cv2
import numpy as np
import tkinter as tk


janela = tk.Tk()
janela.withdraw()  # Esconde a janela principal
caminho_imagem = filedialog.askopenfilename(title="Selecione uma imagem",
                                            filetypes=[("Arquivos de Imagem", "*.png;*.jpg;*.jpeg;*.bmp;*.tiff"),
                                                       ("Todos os Arquivos", "*.*")])

if not caminho_imagem:
    print("Nenhuma imagem selecionada. Encerrando.")
    janela.destroy()
    raise SystemExit

# 1. Carregue e pré-processe (como antes)
img = cv2.imread(caminho_imagem, cv2.IMREAD_GRAYSCALE)
blur = cv2.GaussianBlur(img, (3, 3), 0)

# mascara
h, w = img.shape
mask = np.ones((h, w), dtype=np.uint8) * 255

# 2. Define retângulo central inferior onde está a morsa
rect_width  = int(0.4 * w)   # 40% da largura
rect_height = int(0.1 * h)   # 10% da altura

x1 = int((w - rect_width) / 2)      # começa no meio
x2 = x1 + rect_width
y2 = h                              # borda inferior
y1 = y2 - rect_height               # sobe a altura do retângulo

# zera essa região na máscara (ignorar morsa)
mask[y1:y2, x1:x2] = 0
img_masked = cv2.bitwise_and(img, img, mask=mask)

sobelx = cv2.Sobel(img_masked, cv2.CV_64F, 1, 0, ksize=3)
sobely = cv2.Sobel(img_masked, cv2.CV_64F, 0, 1, ksize=3)
sobel_mag = np.uint8(255 * np.sqrt(sobelx**2 + sobely**2) / np.max(np.sqrt(sobelx**2 + sobely**2)))

# 2. Threshold para bordas binárias
_, thresh = cv2.threshold(sobel_mag, 80, 255, cv2.THRESH_BINARY)

# 3. Encontre contornos
contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# 4. Filtre a maior viga (por área)
if contours:
    maior_contour = max(contours, key=cv2.contourArea)  # Maior área [web:31][web:32]
    area_maior = cv2.contourArea(maior_contour)
    print(f"Área da viga maior: {area_maior:.0f} pixels")
    
    # 5. Crie máscara só da viga
    mask_viga = np.zeros_like(img)
    cv2.drawContours(mask_viga, [maior_contour], -1, 255, thickness=cv2.FILLED)  # Preenche [web:37]
    
    # 6. Highlight na imagem original (cor sobre grayscale)
    img_color = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    cv2.drawContours(img_color, [maior_contour], -1, (0, 255, 0), 5)  # Verde grosso
    
    # 7. Isole só a viga (fundo preto)
    viga_isolada = cv2.bitwise_and(img_color, img_color, mask=mask_viga)
    
    cv2.imshow('Viga isolada', viga_isolada)
    cv2.imshow('Highlight original', img_color)
    
    cv2.imshow('Máscara da Viga', img_masked)
    cv2.waitKey(0)