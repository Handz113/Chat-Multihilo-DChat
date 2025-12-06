from customtkinter import CTkLabel, CTkEntry, CTkButton, CTkFrame
from design_constants import (
    COLOR_BOTON, COLOR_BOTON_HOVER, COLOR_LINK, 
    COLOR_ENTRADA_OSCURA
)

def create_login_widgets(parent_frame, login_command, show_register_command, show_recovery_command):
    CTkLabel(parent_frame, text="¡Bienvenido!", font=("Arial", 28, "bold"), text_color="white").pack(pady=20)
    CTkLabel(parent_frame, text="Usuario", font=("Arial", 12), text_color="white").pack(anchor="w", padx=40)
    login_user_entry = CTkEntry(parent_frame, width=300, font=("Arial", 14), height=40, fg_color=COLOR_ENTRADA_OSCURA, text_color="white", border_width=1, corner_radius=8)
    login_user_entry.pack(padx=40, pady=(0, 15))
    CTkLabel(parent_frame, text="Contraseña", font=("Arial", 12), text_color="white").pack(anchor="w", padx=40)
    login_pass_entry = CTkEntry(parent_frame, width=300, show="*", font=("Arial", 14), height=40, fg_color=COLOR_ENTRADA_OSCURA, text_color="white", border_width=1, corner_radius=8)
    login_pass_entry.pack(padx=40, pady=0)
    CTkButton(parent_frame, text="¿Olvidó su Contraseña?", font=("Arial", 11), fg_color="transparent", text_color=COLOR_LINK, hover=False, anchor="e", width=300, command=show_recovery_command).pack(pady=0, padx=40)
    login_button = CTkButton(parent_frame, text="Iniciar Sesión", font=("Arial", 14, "bold"), fg_color=COLOR_BOTON, hover_color=COLOR_BOTON_HOVER, command=login_command, height=40)
    login_button.pack(pady=20, fill="x", padx=40)
    CTkLabel(parent_frame, text="¿No tienes una cuenta?", text_color="white").pack()
    CTkButton(parent_frame, text="Registrarse", font=("Arial", 11, "underline"), fg_color="transparent", text_color=COLOR_LINK, hover=False, command=show_register_command).pack()
    return {"user_entry": login_user_entry, "pass_entry": login_pass_entry, "login_button": login_button}

def create_register_widgets(parent_frame, register_command, show_login_command):
    CTkLabel(parent_frame, text="Crear Cuenta", font=("Arial", 28, "bold"), text_color="white").pack(pady=10)
    CTkLabel(parent_frame, text="Nombre de Usuario", font=("Arial", 12), text_color="white").pack(anchor="w", padx=40)
    reg_user_entry = CTkEntry(parent_frame, width=300, height=35, fg_color=COLOR_ENTRADA_OSCURA, text_color="white", border_width=1, corner_radius=8)
    reg_user_entry.pack(padx=40, pady=(0, 10))
    CTkLabel(parent_frame, text="Contraseña", font=("Arial", 12), text_color="white").pack(anchor="w", padx=40)
    reg_pass_entry = CTkEntry(parent_frame, width=300, show="*", height=35, fg_color=COLOR_ENTRADA_OSCURA, text_color="white", border_width=1, corner_radius=8)
    reg_pass_entry.pack(padx=40, pady=(0, 10))
    CTkLabel(parent_frame, text="Confirmar Contraseña", font=("Arial", 12), text_color="white").pack(anchor="w", padx=40)
    reg_confirm_entry = CTkEntry(parent_frame, width=300, show="*", height=35, fg_color=COLOR_ENTRADA_OSCURA, text_color="white", border_width=1, corner_radius=8)
    reg_confirm_entry.pack(padx=40, pady=(0, 10))
    CTkLabel(parent_frame, text="Pregunta de Seguridad", font=("Arial", 12), text_color="#AAAAAA").pack(anchor="w", padx=40)
    reg_quest_entry = CTkEntry(parent_frame, width=300, height=35, fg_color=COLOR_ENTRADA_OSCURA, text_color="white", border_width=1, corner_radius=8)
    reg_quest_entry.pack(padx=40, pady=(0, 10))
    CTkLabel(parent_frame, text="Respuesta de Seguridad", font=("Arial", 12), text_color="#AAAAAA").pack(anchor="w", padx=40)
    reg_ans_entry = CTkEntry(parent_frame, width=300, height=35, show="*", fg_color=COLOR_ENTRADA_OSCURA, text_color="white", border_width=1, corner_radius=8)
    reg_ans_entry.pack(padx=40, pady=(0, 15))
    register_button = CTkButton(parent_frame, text="Registrarse", font=("Arial", 14, "bold"), fg_color=COLOR_BOTON, hover_color=COLOR_BOTON_HOVER, command=register_command, height=40)
    register_button.pack(pady=10, fill="x", padx=40)
    CTkButton(parent_frame, text="Volver al Login", font=("Arial", 11, "underline"), fg_color="transparent", text_color=COLOR_LINK, hover=False, command=show_login_command).pack()
    return {"user_entry": reg_user_entry, "pass_entry": reg_pass_entry, "confirm_entry": reg_confirm_entry, "quest_entry": reg_quest_entry, "ans_entry": reg_ans_entry, "register_button": register_button}

def create_recovery_widgets(parent_frame, search_command, reset_command, show_login_command):
    CTkLabel(parent_frame, text="Recuperar Acceso", font=("Arial", 24, "bold"), text_color="white").pack(pady=20)
    step1_frame = CTkFrame(parent_frame, fg_color="transparent")
    step1_frame.pack(fill="x", padx=40)
    CTkLabel(step1_frame, text="1. Ingresa tu Usuario", font=("Arial", 12), text_color="white", anchor="w").pack(fill="x")
    rec_user_entry = CTkEntry(step1_frame, width=200, height=35, fg_color=COLOR_ENTRADA_OSCURA, text_color="white")
    rec_user_entry.pack(side="left", fill="x", expand=True, pady=5)
    CTkButton(step1_frame, text="Buscar", width=60, height=35, fg_color="#444", command=search_command).pack(side="right", padx=(10,0))
    lbl_question = CTkLabel(parent_frame, text="Pregunta: (Ingresa usuario primero)", font=("Arial", 12, "italic"), text_color="#00AFFF")
    lbl_question.pack(pady=15, padx=40, anchor="w")
    CTkLabel(parent_frame, text="2. Respuesta de Seguridad", font=("Arial", 12), text_color="white").pack(anchor="w", padx=40)
    rec_ans_entry = CTkEntry(parent_frame, width=300, height=35, fg_color=COLOR_ENTRADA_OSCURA, text_color="white", show="*")
    rec_ans_entry.pack(padx=40, pady=(0, 10))
    CTkLabel(parent_frame, text="3. Nueva Contraseña", font=("Arial", 12), text_color="white").pack(anchor="w", padx=40)
    rec_new_pass = CTkEntry(parent_frame, width=300, height=35, fg_color=COLOR_ENTRADA_OSCURA, text_color="white", show="*")
    rec_new_pass.pack(padx=40, pady=(0, 20))
    btn_reset = CTkButton(parent_frame, text="Restablecer Contraseña", font=("Arial", 14, "bold"), fg_color=COLOR_BOTON, hover_color=COLOR_BOTON_HOVER, command=reset_command, height=40)
    btn_reset.pack(fill="x", padx=40)
    CTkButton(parent_frame, text="Cancelar / Volver", font=("Arial", 11), fg_color="transparent", text_color=COLOR_LINK, hover=False, command=show_login_command).pack(pady=10)
    return {"user_entry": rec_user_entry, "lbl_question": lbl_question, "ans_entry": rec_ans_entry, "new_pass_entry": rec_new_pass, "reset_btn": btn_reset}