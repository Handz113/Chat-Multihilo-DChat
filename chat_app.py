from customtkinter import *
from CTkMessagebox import CTkMessagebox
import tkinter as tk
import queue
from PIL import Image
import threading 
import json

from network_manager import NetworkManager
import auth 
from design_constants import *

class ChatApp(CTk):

    def __init__(self):
        super().__init__()
        self.title("Chat Seguro - Admin Control")
        self.geometry("400x600") 
        set_appearance_mode("dark")
        set_default_color_theme("blue")
        
        self.alias = ""
        self.cola_mensajes = queue.Queue()
        self.network_manager = NetworkManager(self.cola_mensajes)
        
        # --- NUEVO: DEBOUNCE PARA REDIMENSIONAMIENTO ---
        self.resize_after_id = None
        self.RESIZE_DELAY = 200  # millisegundos
        
        try:
            self.original_image = Image.open(BACKGROUND_IMAGE_PATH)
            self.background_image_ctk = CTkImage(self.original_image, size=(800, 800)) 
            self.background_label = CTkLabel(self, image=self.background_image_ctk, text="")
            self.background_label.place(x=0, y=0, relwidth=1, relheight=1)
            self.bind("<Configure>", self._resize_background_image)
        except:
            self.original_image = None
            self.background_label = None

        self.login_frame = CTkFrame(self, fg_color="transparent")
        w_login = auth.create_login_widgets(self.login_frame, self.on_login_click, self.show_register, self.show_recovery)
        self.login_user = w_login["user_entry"]
        self.login_pass = w_login["pass_entry"]
        self.btn_login = w_login["login_button"]
        
        self.reg_frame = CTkFrame(self, fg_color="transparent")
        w_reg = auth.create_register_widgets(self.reg_frame, self.on_register_click, self.show_login)
        self.reg_user = w_reg["user_entry"]
        self.reg_pass = w_reg["pass_entry"]
        self.reg_conf = w_reg["confirm_entry"]
        self.reg_quest = w_reg["quest_entry"]
        self.reg_ans = w_reg["ans_entry"]
        self.btn_reg = w_reg["register_button"]

        self.rec_frame = CTkFrame(self, fg_color="transparent")
        w_rec = auth.create_recovery_widgets(self.rec_frame, self.on_rec_search_click, self.on_rec_reset_click, self.show_login)
        self.rec_user = w_rec["user_entry"]
        self.rec_lbl_q = w_rec["lbl_question"]
        self.rec_ans = w_rec["ans_entry"]
        self.rec_new_pass = w_rec["new_pass_entry"]
        
        self.chat_frame = CTkFrame(self, fg_color=COLOR_FONDO_CHAT)
        
        self.show_login()
        self.after(100, self.procesar_cola)

    def _resize_background_image(self, event):
        """Redimensiona imagen de fondo con debounce de 200ms"""
        # Cancelar el anterior scheduled resize si existe
        if self.resize_after_id is not None:
            self.after_cancel(self.resize_after_id)
        
        # Programar nuevo resize después de 200ms de inactividad
        self.resize_after_id = self.after(self.RESIZE_DELAY, self._do_resize_background, event.width, event.height)

    def _do_resize_background(self, width, height):
        """Ejecuta el redimensionamiento real de la imagen"""
        if self.original_image and self.background_label:
            if width == 0 or height == 0:
                return
            
            try:
                res_img = self.original_image.resize((width, height), Image.Resampling.LANCZOS)
                self.bg_ctk = CTkImage(light_image=res_img, dark_image=res_img, size=(width, height))
                self.background_label.configure(image=self.bg_ctk)
                self.background_label.lower()
            except Exception as e:
                print(f"Error redimensionando imagen: {e}")
        
        self.resize_after_id = None

    # --- NAVEGACIÓN ---
    def show_login(self):
        # Ocultar otras pantallas
        self.reg_frame.place_forget()
        self.chat_frame.place_forget()
        self.rec_frame.place_forget()
        
        # Fondo
        if self.background_label: 
            self.background_label.place(x=0, y=0, relwidth=1, relheight=1)
            
        self.geometry("400x600")
        
        # Reseteamos el botón para asegurar que siempre esté disponible al volver
        self.btn_login.configure(state="normal", text="Iniciar Sesión")
        
        self.login_frame.place(relx=0.5, rely=0.5, anchor="center")
        self.login_frame.tkraise()

    def show_register(self):
        self.login_frame.place_forget(); self.rec_frame.place_forget()
        self.reg_frame.place(relx=0.5, rely=0.5, anchor="center"); self.reg_frame.tkraise()

    def show_recovery(self):
        self.login_frame.place_forget(); self.reg_frame.place_forget()
        self.rec_frame.place(relx=0.5, rely=0.5, anchor="center"); self.rec_frame.tkraise()
        
    def show_chat(self):
        self.login_frame.place_forget(); self.reg_frame.place_forget(); self.rec_frame.place_forget()
        if self.background_label: self.background_label.place_forget()
        if not self.attributes('-fullscreen'): self.geometry("900x600")
        self.chat_frame.place(x=0, y=0, relwidth=1, relheight=1)
        
        # Crear estructura base del chat
        self._crear_interfaz_chat_base()
        
        self.network_manager.start_listening()

    # --- UI CHAT ---
    def _crear_interfaz_chat_base(self):
        for widget in self.chat_frame.winfo_children(): widget.destroy()

        # 1. Barra Lateral (Contenedor vacío, se llena dinámicamente)
        self.barra_lateral = CTkFrame(self.chat_frame, width=200, fg_color=COLOR_BARRA_LATERAL_CHAT, corner_radius=0)
        self.barra_lateral.pack(side="left", fill="y")
        self.barra_lateral.pack_propagate(False)
        
        CTkLabel(self.barra_lateral, text="Salas", font=("Arial", 16, "bold"), text_color=COLOR_TEXTO_CHAT).pack(pady=20, padx=20, anchor="w")
        
        self.contenedor_botones_salas = CTkScrollableFrame(self.barra_lateral, fg_color="transparent")
        self.contenedor_botones_salas.pack(fill="both", expand=True)

        # 2. Panel Derecho
        self.panel_derecho = CTkFrame(self.chat_frame, width=150, fg_color="#111111", corner_radius=0)
        self.panel_derecho.pack(side="right", fill="y"); self.panel_derecho.pack_propagate(False)
        CTkLabel(self.panel_derecho, text="Opciones", font=("Arial", 16, "bold"), text_color="white").pack(pady=20)
        CTkButton(self.panel_derecho, text="Ver miembros", fg_color="#333333", hover_color="#444444", width=120, command=self.ver_miembros).pack(pady=10)
        CTkButton(self.panel_derecho, text="Salir", fg_color="#B00020", hover_color="#800017", width=120, command=self.on_salir_chat).pack(pady=20, side="bottom", anchor="s")

        # 3. Centro
        self.chat_area_frame = CTkFrame(self.chat_frame, fg_color=COLOR_FONDO_CHAT, corner_radius=0)
        self.chat_area_frame.pack(fill="both", expand=True)
        
        self.chat_header = CTkLabel(self.chat_area_frame, text="...", font=("Arial", 18, "bold"), text_color=COLOR_TEXTO_CHAT, anchor="w", height=40, fg_color=COLOR_HEADER_CHAT, padx=20)
        self.chat_header.pack(fill="x")

        self.pin_frame = CTkFrame(self.chat_area_frame, height=30, fg_color="#2B3A42", corner_radius=0)
        self.pin_frame.pack(fill="x"); self.pin_frame.pack_propagate(False) 
        self.pin_icon = CTkLabel(self.pin_frame, text="📌 FIJADO:", font=("Arial", 12, "bold"), text_color="#FFA500")
        self.pin_icon.pack(side="left", padx=(20, 5))
        self.pin_label = CTkLabel(self.pin_frame, text="(Ningún mensaje fijado)", font=("Arial", 12, "italic"), text_color="#DDDDDD", anchor="w")
        self.pin_label.pack(side="left", fill="x", expand=True)

        self.chat_area = CTkTextbox(self.chat_area_frame, state="disabled", font=("Arial", 12), wrap=tk.WORD, fg_color=COLOR_FONDO_CHAT, text_color=COLOR_TEXTO_CHAT)
        self.chat_area.pack(fill="both", expand=True, padx=10, pady=10)
        self.chat_area.tag_config("sistema", foreground="gray"); self.chat_area.tag_config("alias", foreground=COLOR_TEXTO_ALIAS)

        frm_in = CTkFrame(self.chat_area_frame, fg_color="transparent")
        frm_in.pack(fill="x", padx=10, pady=10)
        self.msg_entry = CTkEntry(frm_in, font=("Arial", 12), height=40, placeholder_text="Escribe /help...", fg_color=COLOR_HEADER_CHAT, text_color=COLOR_TEXTO_CHAT)
        self.msg_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.msg_entry.bind("<Return>", self.on_enviar_mensaje) 
        CTkButton(frm_in, text="Enviar", width=80, height=40, command=self.on_enviar_mensaje).pack(side="right")

    # --- DINÁMICA DE SALAS ---
    def actualizar_lista_salas(self, lista_nombres):
        # Limpiar botones viejos
        for widget in self.contenedor_botones_salas.winfo_children():
            widget.destroy()
        
        # Crear nuevos
        for sala in lista_nombres:
            btn = CTkButton(self.contenedor_botones_salas, text=sala, font=("Arial", 14), anchor="w", fg_color="transparent", text_color=COLOR_TEXTO_CHAT, hover_color="#333333", command=lambda s=sala: self.cambiar_sala(s))
            btn.pack(fill="x", padx=5, pady=2)

    def cambiar_sala(self, sala):
        self.chat_area.configure(state="normal")
        self.chat_area.delete("1.0", tk.END)
        self.chat_area.insert(tk.END, f"[SISTEMA] Conectando a {sala}...\n", "sistema")
        self.chat_area.configure(state="disabled")
        self.pin_label.configure(text="Cargando...")
        self.network_manager.send_msg(f"/join {sala}")
        if hasattr(self, 'chat_header'): self.chat_header.configure(text=sala)

    # --- FUNCIONALIDAD ---
    def ver_miembros(self): self.network_manager.solicitar_usuarios()

    def mostrar_ventana_miembros(self, json_data):
        try:
            datos = json.loads(json_data)
            top = CTkToplevel(self)
            top.title("Miembros en Línea"); top.geometry("400x500"); top.grab_set() 
            CTkLabel(top, text="Usuarios Conectados", font=("Arial", 20, "bold")).pack(pady=10)
            scroll = CTkScrollableFrame(top, width=350, height=400); scroll.pack(padx=10, pady=10, fill="both", expand=True)
            for sala, usuarios in datos.items():
                CTkLabel(scroll, text=sala, font=("Arial", 16, "bold"), text_color="#00AFFF", anchor="w").pack(fill="x", pady=(10, 5))
                if not usuarios: CTkLabel(scroll, text="   (Vacío)", font=("Arial", 12, "italic"), text_color="gray", anchor="w").pack(fill="x")
                else:
                    for u in usuarios:
                        color = "white"
                        if "[ADMIN]" in u: color = "#FFD700" 
                        elif "[DOCENTE]" in u: color = "#00FF7F" 
                        CTkLabel(scroll, text=f"   • {u}", font=("Arial", 14), text_color=color, anchor="w").pack(fill="x", pady=2)
        except Exception as e: print(f"Error parseando usuarios: {e}")

    def on_enviar_mensaje(self, event=None):
        m = self.msg_entry.get()
        if m:
            if self.network_manager.send_msg(m):
                self.chat_area.configure(state="normal")
                self.chat_area.insert(tk.END, f"{self.alias}: ", "alias"); self.chat_area.insert(tk.END, f"{m}\n")
                self.chat_area.configure(state="disabled"); self.chat_area.see(tk.END)
            self.msg_entry.delete(0, tk.END)

    def on_salir_chat(self):
        self.network_manager.disconnect(); self.show_login()
        self.alias = ""; self.login_user.delete(0, tk.END); self.login_pass.delete(0, tk.END)

    def on_login_click(self):
        u, p = self.login_user.get(), self.login_pass.get()
        if u and p: 
            self.btn_login.configure(state="disabled", text="...")
            threading.Thread(target=self.network_manager.login, args=(u, p), daemon=True).start()

    def on_register_click(self):
        u, p, c = self.reg_user.get(), self.reg_pass.get(), self.reg_conf.get()
        q, a = self.reg_quest.get(), self.reg_ans.get()
        if not all([u,p,c,q,a]): return CTkMessagebox(title="Error", message="Faltan datos")
        if p != c: return CTkMessagebox(title="Error", message="Pass no coincide")
        self.btn_reg.configure(state="disabled", text="...")
        threading.Thread(target=self.network_manager.register, args=(u, p, q, a), daemon=True).start()

    def on_rec_search_click(self):
        u = self.rec_user.get()
        if u: 
            self.rec_lbl_q.configure(text="Buscando...")
            threading.Thread(target=self.network_manager.recover_step1, args=(u,), daemon=True).start()

    def on_rec_reset_click(self):
        u, a, np = self.rec_user.get(), self.rec_ans.get(), self.rec_new_pass.get()
        if all([u, a, np]): threading.Thread(target=self.network_manager.recover_step2, args=(u, a, np), daemon=True).start()

    def procesar_cola(self):
        try:
            while not self.cola_mensajes.empty():
                msg = self.cola_mensajes.get()
                if msg.startswith("[LOGIN]"):
                    if "Bienvenido" in msg: self.alias = self.login_user.get(); self.show_chat()
                    else: CTkMessagebox(title="Error", message=msg.split(" ", 1)[1]); self.btn_login.configure(state="normal", text="Login")
                elif msg.startswith("[REGISTRO]"):
                    CTkMessagebox(title="Info", message=msg)
                    if "exitoso" in msg: self.show_login()
                    self.btn_reg.configure(state="normal", text="Registrar")
                elif msg.startswith("[RECUPERACION_DATA]"):
                    d = msg.split(" ", 1)[1]
                    self.rec_lbl_q.configure(text=f"Pregunta: {d.split(':', 1)[1]}" if "PREGUNTA:" in d else "Usuario no encontrado")
                elif msg.startswith("[RECUPERACION_RESULT]"):
                    CTkMessagebox(title="Info", message=msg.split(" ", 1)[1])
                    if "EXITO" in msg: self.show_login()
                elif msg.startswith("PIN_UPDATE:"):
                    texto_pin = msg.split(":", 1)[1]
                    if hasattr(self, 'pin_label'):
                        if texto_pin: self.pin_label.configure(text=texto_pin, font=("Arial", 12, "bold"), text_color="white")
                        else: self.pin_label.configure(text="(Ningún mensaje fijado)", font=("Arial", 12, "italic"), text_color="#888888")
                
                # --- HISTORIAL EN LOTE (OPTIMIZADO) ---
                elif msg.startswith("HISTORY_BATCH:"):
                    json_historial = msg.split(":", 1)[1]
                    try:
                        datos = json.loads(json_historial)
                        if hasattr(self, 'chat_area'):
                            mensajes = datos.get("mensajes", [])
                            if mensajes:
                                # Cambiar estado una sola vez
                                self.chat_area.configure(state="normal")
                                
                                # Construir string con todos los mensajes
                                contenido = ""
                                for m in mensajes:
                                    contenido += m + "\n"
                                
                                # Insertar todo de una vez
                                self.chat_area.insert(tk.END, contenido)
                                
                                # Cambiar estado y desplazar
                                self.chat_area.configure(state="disabled")
                                self.chat_area.see(tk.END)
                    except Exception as e:
                        print(f"Error parseando historial: {e}")
                
                elif msg.startswith("ROOMS_UPDATE:"):
                    json_salas = msg.split(":", 1)[1]
                    try:
                        lista = json.loads(json_salas)
                        if hasattr(self, 'actualizar_lista_salas'):
                            self.actualizar_lista_salas(lista)
                    except: pass
                
                elif msg.startswith("USERS_LIST:"):
                    json_data = msg.split(":", 1)[1]
                    self.mostrar_ventana_miembros(json_data)
                elif hasattr(self, 'chat_area'):
                    self.chat_area.configure(state="normal")
                    if msg.startswith("[SISTEMA]"): self.chat_area.insert(tk.END, msg + "\n", "sistema")
                    elif ":" in msg:
                        p = msg.split(":", 1)
                        if len(p)==2 and p[0] != self.alias: self.chat_area.insert(tk.END, f"{p[0]}:", "alias"); self.chat_area.insert(tk.END, f"{p[1]}\n")
                        elif len(p)==2 and p[0] == self.alias: pass 
                        else: self.chat_area.insert(tk.END, msg + "\n")
                    else: self.chat_area.insert(tk.END, msg + "\n")
                    self.chat_area.configure(state="disabled"); self.chat_area.see(tk.END)
        finally:
            self.after(100, self.procesar_cola)

    def on_closing(self):
        # Cancelar resize pendiente si existe
        if self.resize_after_id is not None:
            self.after_cancel(self.resize_after_id)
        
        try: self.network_manager.disconnect()
        except: pass
        self.destroy()

if __name__ == "__main__":
    app = ChatApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
