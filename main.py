import pygame
import speech_recognition as sr
import pyttsx3
import cv2
import mediapipe as mp
import threading
import sys
import time

# Inicializar pygame
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Mono Controlado por Voz y Cámara")

# Cargar imágenes del mono
try:
    mono_normal = pygame.image.load("mono_norm.png")
    mono_bailando = pygame.image.load("mono_inv.PNG")
    mono_normal = pygame.transform.scale(mono_normal, (80, 80))
    mono_bailando = pygame.transform.scale(mono_bailando, (80, 80))
except:
    print("Error cargando imágenes. Usando placeholders.")
    mono_normal = pygame.Surface((80, 80))
    mono_normal.fill((255, 0, 0))
    mono_bailando = pygame.Surface((80, 80))
    mono_bailando.fill((0, 255, 0))

# Variables del mono
x, y = WIDTH // 2, HEIGHT // 2
vel = 15
bailando = False
running = True
modo = "menu"
comando = None

# Configuración de voz
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

# Configuración de MediaPipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1)
mp_drawing = mp.solutions.drawing_utils

# Función para hablar
def hablar(mensaje):
    def hablar_hilo():
        print(f"🔊: {mensaje}")
        engine.say(mensaje)
        engine.runAndWait()
    threading.Thread(target=hablar_hilo, daemon=True).start()

# Función para reconocimiento de voz
def reconocer_voz():
    global comando, bailando, x, y
    r = sr.Recognizer()
    while running and modo == "voz":
        try:
            with sr.Microphone() as source:
                print("Escuchando...")
                r.adjust_for_ambient_noise(source)
                audio = r.listen(source, timeout=3, phrase_time_limit=2)
            
            comando = r.recognize_google(audio, language="es-ES").lower()
            print(f"Comando: {comando}")
            hablar(comando)
            
            if "arriba" in comando:
                y = max(0, y - vel)
                bailando = False
            elif "abajo" in comando:
                y = min(HEIGHT - 80, y + vel)
                bailando = False
            elif "izquierda" in comando:
                x = max(0, x - vel)
                bailando = False
            elif "derecha" in comando:
                x = min(WIDTH - 80, x + vel)
                bailando = False
            elif "bailar" in comando:
                bailando = not bailando
                hablar("Bailando!" if bailando else "Dejo de bailar")
                
        except (sr.UnknownValueError, sr.WaitTimeoutError):
            continue
        except Exception as e:
            print(f"Error en voz: {e}")

# Función para detección de cámara
def detectar_manos():
    global x, y, bailando
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: No se pudo abrir la cámara")
        return
    
    while running and modo == "camara":
        success, image = cap.read()
        if not success:
            continue
            
        try:
            image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
            image.flags.writeable = False
            results = hands.process(image)
            
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    landmark = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                    x = int(landmark.x * WIDTH)
                    y = int(landmark.y * HEIGHT)
                    
                    thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
                    index_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP]
                    bailando = thumb_tip.y < index_mcp.y
                    
        except Exception as e:
            print(f"Error en detección: {e}")
            continue
            
    cap.release()

# Función para dibujar el menú
def dibujar_menu():
    screen.fill((240, 240, 240))
    font = pygame.font.SysFont('Arial', 40)
    
    titulo = font.render("Selecciona Modo de Control", True, (0, 0, 0))
    screen.blit(titulo, (WIDTH//2 - titulo.get_width()//2, 100))
    
    opciones = [
        ("Control por Voz", (100, 200)),
        ("Control por Cámara", (100, 300)),
        ("Salir", (100, 400))
    ]
    
    for i, (texto, pos) in enumerate(opciones):
        color = (0, 0, 200) if i == 0 else (0, 0, 100)
        btn = font.render(texto, True, color)
        screen.blit(btn, pos)
    
    pygame.display.flip()

# Bucle principal
def main():
    global modo, running, x, y, bailando
    
    clock = pygame.time.Clock()
    voz_thread = None
    camara_thread = None
    last_switch_time = 0
    
    while running:
        current_time = pygame.time.get_ticks()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    modo = "menu"
                    if voz_thread: voz_thread.join()
                    if camara_thread: camara_thread.join()
            elif event.type == pygame.MOUSEBUTTONDOWN and modo == "menu":
                mouse_pos = pygame.mouse.get_pos()
                if 100 <= mouse_pos[0] <= 400:
                    if 200 <= mouse_pos[1] <= 250:
                        modo = "voz"
                        voz_thread = threading.Thread(target=reconocer_voz, daemon=True)
                        voz_thread.start()
                        hablar("Modo voz activado")
                    elif 300 <= mouse_pos[1] <= 350:
                        modo = "camara"
                        camara_thread = threading.Thread(target=detectar_manos, daemon=True)
                        camara_thread.start()
                        hablar("Modo cámara activado")
                    elif 400 <= mouse_pos[1] <= 450:
                        running = False
        
        if modo == "menu":
            dibujar_menu()
        else:
            screen.fill((255, 255, 255))
            
            # Animación del baile
            if bailando:
                if current_time - last_switch_time > 500:  # Cambia cada 500ms
                    last_switch_time = current_time
                current_img = mono_bailando if (current_time // 500) % 2 == 0 else mono_normal
            else:
                current_img = mono_normal
                
            screen.blit(current_img, (x - current_img.get_width()//2, y - current_img.get_height()//2))
            
            # Mostrar instrucciones
            font = pygame.font.SysFont('Arial', 24)
            instrucciones = font.render("Presiona ESC para volver al menú", True, (0, 0, 0))
            screen.blit(instrucciones, (20, 20))
            
            # Mostrar modo actual
            modo_text = font.render(f"Modo: {modo.upper()}", True, (0, 0, 200))
            screen.blit(modo_text, (WIDTH - modo_text.get_width() - 20, 20))
            
            pygame.display.flip()
        
        clock.tick(60)
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()