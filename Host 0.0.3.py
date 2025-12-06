import socket
import threading
import json
import hashlib
import os
import ssl
import requests
from datetime import datetime

# --- Configuración Inicial ---
usuarios_file = "usuarios.json"
historial_file = "historial.json"
pines_file = "pines.json"
salas_file = "salas.json"

OLLAMA_URL = "http://localhost:11434/api/generate"
MODELO_IA = "llama3.2:3b"

# Verificación de certificados
if not (os.path.exists("server.crt") and os.path.exists("server.key")):
    print("⚠️ ADVERTENCIA: No se encontraron 'server.crt' o 'server.key'.")

# --- Base de Datos Usuarios ---
def cargar_usuarios():
    if not os.path.exists(usuarios_file):
        with open(usuarios_file, "w") as f:
            json.dump({}, f)
    with open(usuarios_file, "r") as f:
        try: return json.load(f)
        except: return {}

def guardar_usuarios(data):
    try:
        with open(usuarios_file, "w") as f: json.dump(data, f, indent=4)
    except Exception as e: print(f"Error guardando usuarios: {e}")

# --- Gestión de Salas (Dinámica) ---
def cargar_nombres_salas():
    if not os.path.exists(salas_file):
        default = ["General", "Equipo 1", "Equipo 2"]
        with open(salas_file, "w") as f: json.dump(default, f)
        return default
    with open(salas_file, "r") as f:
        try: return json.load(f)
        except: return ["General"]

def guardar_nombres_salas(lista_nombres):
    try:
        with open(salas_file, "w") as f: json.dump(lista_nombres, f, indent=4)
    except: pass

# Inicializar estructura en memoria
nombres_guardados = cargar_nombres_salas()
salas = {nombre: [] for nombre in nombres_guardados}
clientes = {} 

# --- Historial ---
def cargar_historial():
    if not os.path.exists(historial_file):
        init = {s: [] for s in salas.keys()}
        with open(historial_file, "w") as f: json.dump(init, f)
        return init
    with open(historial_file, "r") as f:
        try: return json.load(f)
        except: return {}

def registrar_mensaje_historial(sala, mensaje_formateado):
    if sala not in salas: return
    hist = cargar_historial()
    if sala not in hist: hist[sala] = []
    
    hist[sala].append(mensaje_formateado)
    if len(hist[sala]) > 1000: hist[sala] = hist[sala][-1000:]
        
    try:
        with open(historial_file, "w") as f: json.dump(hist, f, indent=4)
    except: pass

def enviar_historial_a_usuario(conn, sala):
    hist = cargar_historial()
    msgs = hist.get(sala, [])
    if not msgs: return
    enviar_privado(conn, f"\n--- 📜 Historial de {sala} ---")
    for m in msgs: enviar_privado(conn, m)
    enviar_privado(conn, "--------------------------------\n")

# --- [NUEVO] LÓGICA DE INTELIGENCIA ARTIFICIAL ---
def generar_resumen_ollama(sala):
    """Lee el historial y solicita un resumen a Llama 3.2"""
    hist = cargar_historial()
    mensajes = hist.get(sala, [])
    
    if not mensajes:
        return "No hay suficientes mensajes para generar un resumen."
    
    # Tomamos los últimos 50 mensajes para no saturar el contexto
    ultimos_mensajes = mensajes[-50:]
    texto_conversacion = "\n".join(ultimos_mensajes)
    
    prompt_sistema = (
        f"Eres un asistente de secretaría técnica. Resume la siguiente conversación del chat de la sala '{sala}'. "
        "Ignora los mensajes de sistema como [ENTRÓ], [SALIÓ]. "
        "Enumera los puntos clave y decisiones. Sé breve y profesional en español."
    )
    
    payload = {
        "model": MODELO_IA,
        "prompt": f"{prompt_sistema}\n\nConversación:\n{texto_conversacion}",
        "stream": False
    }
    
    try:
        print(f"🤖 [IA] Generando resumen para {sala}...")
        # Timeout de 90 segundos para darle tiempo a la Raspberry Pi
        response = requests.post(OLLAMA_URL, json=payload, timeout=90) 
        response.raise_for_status()
        resultado = response.json()
        return resultado.get("response", "La IA no devolvió respuesta.")
    except requests.exceptions.ConnectionError:
        return "❌ Error: El servicio de IA (Ollama) no está corriendo en el servidor."
    except Exception as e:
        return f"❌ Error generando resumen: {str(e)}"

# --- Pines ---
def cargar_pines():
    if not os.path.exists(pines_file):
        init = {s: "" for s in salas.keys()}
        with open(pines_file, "w") as f: json.dump(init, f)
        return init
    with open(pines_file, "r") as f:
        try: return json.load(f)
        except: return {}

def guardar_pin(sala, mensaje):
    pines = cargar_pines()
    pines[sala] = mensaje
    try:
        with open(pines_file, "w") as f: json.dump(pines, f, indent=4)
    except: pass

def broadcast_pin(sala, mensaje):
    comando = f"PIN_UPDATE:{mensaje}"
    if sala in salas:
        for conn in salas[sala]:
            try: conn.send(comando.encode("utf-8"))
            except: pass

# --- Utilidades de Red ---
def broadcast(sala, mensaje, remitente_conn=None):
    hora = datetime.now().strftime("%H:%M")
    msg_final = f"[{hora}] {mensaje}"
    if sala in salas: registrar_mensaje_historial(sala, msg_final)
    if sala not in salas: return
    for conn in list(salas[sala]):
        if conn != remitente_conn:
            try: conn.send(msg_final.encode("utf-8"))
            except: remover_cliente(conn)

def broadcast_lista_salas():
    lista = list(salas.keys())
    json_salas = json.dumps(lista)
    msg = f"ROOMS_UPDATE:{json_salas}"
    for conn in clientes.keys():
        try: conn.send(msg.encode("utf-8"))
        except: pass

def enviar_privado(conn, mensaje):
    try: conn.send(mensaje.encode("utf-8"))
    except: pass

def remover_cliente(conn):
    if conn in clientes:
        alias = clientes[conn]["alias"]
        sala = clientes[conn]["sala"]
        if sala in salas and conn in salas[sala]: salas[sala].remove(conn)
        del clientes[conn]
    try: conn.close()
    except: pass

# --- Auth ---
def registrar_usuario(conn, user, hashed_pwd, pregunta, hashed_resp):
    usuarios = cargar_usuarios()
    if user in usuarios:
        conn.send("Usuario ya existe.\n".encode("utf-8"))
        return False 
    else:
        rol_inicial = "estudiante"
        if len(usuarios) == 0: rol_inicial = "admin"
        usuarios[user] = {
            "pass": hashed_pwd, "rol": rol_inicial, "banned": False,
            "pregunta": pregunta, "resp_hash": hashed_resp      
        }
        guardar_usuarios(usuarios)
        conn.send(f"Registro exitoso. Rol asignado: {rol_inicial.upper()}.".encode("utf-8"))
        return True 

def login_verificacion(user, hashed_pwd):
    usuarios = cargar_usuarios()
    if user in usuarios:
        datos = usuarios[user]
        if datos["pass"] == hashed_pwd:
            if datos.get("banned", False): return "BANNED"
            return datos.get("rol", "estudiante")
    return None

# --- Comandos ---
def procesar_comando(conn, mensaje, alias, rol, sala_actual):
    partes = mensaje.split(" ")
    comando = partes[0].lower()
    es_staff = (rol == "admin" or rol == "docente")
    es_admin = (rol == "admin")

    # [NUEVO] COMANDO IA /resume
    if comando == "/resume":
        enviar_privado(conn, "🤖 La IA está leyendo el historial... esto puede tardar unos segundos.")
        # Se ejecuta en el hilo del cliente, está bien para este uso
        resumen = generar_resumen_ollama(sala_actual)
        
        enviar_privado(conn, f"\n✨ --- RESUMEN IA ({sala_actual}) --- ✨\n")
        enviar_privado(conn, resumen)
        enviar_privado(conn, "\n----------------------------------------\n")
        return True

    # CREAR SALA
    if comando == "/crear":
        if not es_admin:
            enviar_privado(conn, "[ERROR] Solo Admin.")
            return True
        nombre_sala = " ".join(partes[1:])
        if not nombre_sala:
            enviar_privado(conn, "Uso: /crear [nombre]")
            return True
        if nombre_sala in salas:
            enviar_privado(conn, "❌ La sala ya existe.")
            return True
        salas[nombre_sala] = []
        guardar_nombres_salas(list(salas.keys()))
        broadcast_lista_salas()
        enviar_privado(conn, f"✅ Sala '{nombre_sala}' creada.")
        return True

    # BORRAR SALA
    if comando == "/borrar":
        if not es_admin:
            enviar_privado(conn, "[ERROR] Solo Admin.")
            return True
        nombre_sala = " ".join(partes[1:])
        if nombre_sala not in salas:
            enviar_privado(conn, "❌ Sala no encontrada.")
            return True
        if len(salas) <= 1:
            enviar_privado(conn, "⚠️ No puedes borrar la última sala.")
            return True
        sala_destino = list(salas.keys())[0]
        if sala_destino == nombre_sala: sala_destino = list(salas.keys())[1]
        
        usuarios_afectados = list(salas[nombre_sala])
        for c in usuarios_afectados:
            salas[nombre_sala].remove(c)
            salas[sala_destino].append(c)
            clientes[c]["sala"] = sala_destino
            enviar_privado(c, f"⚠️ La sala actual fue eliminada. Movido a {sala_destino}.")
            enviar_historial_a_usuario(c, sala_destino)
        del salas[nombre_sala]
        guardar_nombres_salas(list(salas.keys()))
        broadcast_lista_salas()
        enviar_privado(conn, f"✅ Sala '{nombre_sala}' eliminada.")
        return True

    # VER MIEMBROS
    if comando == "/get_users":
        lista_equipos = {s: [] for s in salas.keys()}
        for c, datos in clientes.items():
            s_u = datos["sala"]
            if s_u in lista_equipos:
                info = f"{datos['alias']}"
                if datos['rol'] != "estudiante": info += f" [{datos['rol'].upper()}]"
                if datos['muted']: info += " 🔇"
                lista_equipos[s_u].append(info)
        enviar_privado(conn, f"USERS_LIST:{json.dumps(lista_equipos)}")
        return True

    if comando == "/help":
        ayuda = "--- AYUDA ---\n/mirol, /join [sala], /resume (IA)"
        if es_staff: ayuda += "\n(STAFF) /kick, /mute, /unmute, /anuncio, /pin"
        if es_admin: ayuda += "\n(ADMIN) /crear [nombre], /borrar [nombre], /promote, /ban"
        enviar_privado(conn, ayuda)
        return True

    if comando == "/mirol":
        enviar_privado(conn, f"🕵️ Tu rol es: [{rol.upper()}]")
        return True

    if comando == "/join":
        nueva_sala = " ".join(partes[1:]) if len(partes) > 1 else ""
        if nueva_sala in salas:
            if conn in salas[sala_actual]: salas[sala_actual].remove(conn)
            salas[nueva_sala].append(conn)
            clientes[conn]["sala"] = nueva_sala
            enviar_privado(conn, f"[SISTEMA] Entraste a: {nueva_sala}")
            enviar_historial_a_usuario(conn, nueva_sala)
            pines = cargar_pines()
            conn.send(f"PIN_UPDATE:{pines.get(nueva_sala, '')}".encode("utf-8"))
        else: enviar_privado(conn, f"[SISTEMA] Sala no existe.")
        return True

    if comando == "/pin":
        if not es_staff: return True
        texto = " ".join(partes[1:])
        if not texto: return True
        pines = cargar_pines()
        actual = pines.get(sala_actual, "")
        if actual:
            clientes[conn]["pending_pin"] = texto
            enviar_privado(conn, f"⚠️ Ya existe pin. ¿Sobrescribir? (y/n)")
            return True
        else:
            guardar_pin(sala_actual, texto)
            broadcast_pin(sala_actual, texto)
            enviar_privado(conn, "✅ Fijado.")
            return True

    if comando == "/anuncio":
        if not es_staff: return True
        broadcast(sala_actual, f"\n📢 [ANUNCIO] 📢\n{' '.join(partes[1:])}\n")
        return True

    if comando == "/kick":
        if not es_staff: return True
        target = partes[1].lower() if len(partes) > 1 else ""
        for s, d in list(clientes.items()):
            if d["alias"].lower() == target:
                if d["rol"] == "admin": return True
                enviar_privado(s, "🚫 Expulsado.")
                remover_cliente(s)
                enviar_privado(conn, f"✅ {target} expulsado.")
                return True
        return True

    if comando == "/ban":
        if not es_staff: return True
        target = partes[1] if len(partes) > 1 else ""
        usrs = cargar_usuarios()
        if target in usrs:
            if usrs[target]["rol"] == "admin": return True
            usrs[target]["banned"] = True
            guardar_usuarios(usrs)
            for s, d in list(clientes.items()):
                if d["alias"] == target:
                    enviar_privado(s, "⛔ BANEADO.")
                    remover_cliente(s)
            enviar_privado(conn, "✅ Usuario baneado.")
        return True

    if comando == "/unban":
        if not es_admin: return True
        target = partes[1] if len(partes) > 1 else ""
        usrs = cargar_usuarios()
        if target in usrs:
            usrs[target]["banned"] = False
            guardar_usuarios(usrs)
            enviar_privado(conn, "✅ Desbaneado.")
        return True
    
    if comando == "/mute":
        if not es_staff: return True
        target = partes[1].lower() if len(partes) > 1 else ""
        for s, d in clientes.items():
            if d["alias"].lower() == target:
                d["muted"] = True
                enviar_privado(s, "😶 Silenciado.")
                enviar_privado(conn, "✅ Listo.")
                return True
        return True

    if comando == "/unmute":
        if not es_staff: return True
        target = partes[1].lower() if len(partes) > 1 else ""
        for s, d in clientes.items():
            if d["alias"].lower() == target:
                d["muted"] = False
                enviar_privado(s, "🗣️ Liberado.")
                enviar_privado(conn, "✅ Listo.")
                return True
        return True

    if comando == "/promote":
        if not es_admin: return True
        if len(partes) < 3: return True
        target, n_rol = partes[1], partes[2].lower()
        usrs = cargar_usuarios()
        if target in usrs and n_rol in ["admin", "docente", "estudiante"]:
            usrs[target]["rol"] = n_rol
            guardar_usuarios(usrs)
            for s, d in clientes.items():
                if d["alias"] == target:
                    d["rol"] = n_rol
                    enviar_privado(s, f"🎖️ Nuevo rol: {n_rol}")
            enviar_privado(conn, f"✅ {target} es ahora {n_rol}.")
        return True

    enviar_privado(conn, "❌ Comando desconocido.")
    return False

# --- MAIN ---
def manejar_cliente(conn, addr):
    print(f"🔒 [CONEXIÓN] {addr}")
    try:
        opcion = conn.recv(1024).decode("utf-8").lower().strip()
        if opcion == "l": 
            conn.send("ACK".encode())
            user = conn.recv(1024).decode().strip()
            conn.send("ACK".encode())
            pwd = conn.recv(1024).decode().strip()
            hashed = hashlib.sha256(pwd.encode()).hexdigest()
            rol = login_verificacion(user, hashed)
            if rol == "BANNED":
                conn.send("⛔ SUSPENDIDA.".encode())
                return
            elif rol:
                conn.send(f"Bienvenido {user} [{rol.upper()}]".encode())
                
                # Asignar a la primera sala disponible
                sala_inicial = list(salas.keys())[0]
                clientes[conn] = {"alias": user, "sala": sala_inicial, "rol": rol, "muted": False, "pending_pin": None}
                salas[sala_inicial].append(conn)
                
                broadcast(sala_inicial, f"[SISTEMA] {user} entró.", conn)
                
                # 1. Enviar Lista de Salas
                json_salas = json.dumps(list(salas.keys()))
                conn.send(f"ROOMS_UPDATE:{json_salas}".encode("utf-8"))
                
                # 2. Historial y Pin
                enviar_historial_a_usuario(conn, sala_inicial)
                pines = cargar_pines()
                conn.send(f"PIN_UPDATE:{pines.get(sala_inicial, '')}".encode("utf-8"))

                while True:
                    data = conn.recv(1024).decode().strip()
                    if not data: break
                    
                    if clientes[conn].get("pending_pin"):
                        if data.lower() in ["y", "s", "si"]:
                            guardar_pin(clientes[conn]["sala"], clientes[conn]["pending_pin"])
                            broadcast_pin(clientes[conn]["sala"], clientes[conn]["pending_pin"])
                            enviar_privado(conn, "✅ Actualizado.")
                        else: enviar_privado(conn, "❌ Cancelado.")
                        clientes[conn]["pending_pin"] = None
                        continue

                    if clientes[conn]["muted"] and not data.startswith("/"):
                        enviar_privado(conn, "😶 Silenciado.")
                        continue

                    if data.startswith("/"):
                        sala_previa = clientes[conn]["sala"]
                        procesar_comando(conn, data, user, rol, sala_previa)
                    else:
                        prefijo = ""
                        if rol == "admin": prefijo = "👑 [ADMIN] "
                        elif rol == "docente": prefijo = "🎓 [DOCENTE] "
                        broadcast(clientes[conn]["sala"], f"{prefijo}{user}: {data}", conn)
                return
            else:
                conn.send("Error credenciales.".encode()); return
        
        elif opcion == "r":
            conn.send("ACK".encode()); u = conn.recv(1024).decode().strip()
            conn.send("ACK".encode()); p = conn.recv(1024).decode().strip()
            conn.send("ACK".encode()); q = conn.recv(1024).decode().strip()
            conn.send("ACK".encode()); r = conn.recv(1024).decode().strip().lower()
            registrar_usuario(conn, u, hashlib.sha256(p.encode()).hexdigest(), q, hashlib.sha256(r.encode()).hexdigest())
        elif opcion == "rec_req":
            conn.send("ACK".encode()); u = conn.recv(1024).decode().strip()
            us = cargar_usuarios()
            conn.send(f"PREGUNTA:{us[u]['pregunta']}".encode() if u in us else "ERROR".encode())
        elif opcion == "rec_reset":
            conn.send("ACK".encode()); u = conn.recv(1024).decode().strip()
            conn.send("ACK".encode()); r = conn.recv(1024).decode().strip().lower()
            conn.send("ACK".encode()); np = conn.recv(1024).decode().strip()
            us = cargar_usuarios()
            if u in us and us[u]["resp_hash"] == hashlib.sha256(r.encode()).hexdigest():
                us[u]["pass"] = hashlib.sha256(np.encode()).hexdigest()
                guardar_usuarios(us); conn.send("EXITO".encode())
            else: conn.send("ERROR".encode())
    except: pass
    finally: remover_cliente(conn)

def main():
    # [NUEVO] Verificación de IA
    try:
        requests.get("http://localhost:11434")
        print("🤖 [IA] Ollama detectado y listo.")
    except:
        print("⚠️ [IA] OLLAMA NO RESPONDE. El comando /resume fallará.")
        print("   -> Asegúrate de ejecutar 'ollama serve' en la Raspberry.")

    try:
        ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ctx.load_cert_chain("server.crt", "server.key")
    except:
        print("❌ Error SSL: No se encuentran las llaves. El servidor no iniciará.")
        return
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("0.0.0.0", 5000))
    s.listen(5)
    print("📌 [SERVIDOR COMPLETO] Listo en puerto 5000.")
    while True:
        c, a = s.accept()
        threading.Thread(target=manejar_cliente, args=(ctx.wrap_socket(c, server_side=True), a), daemon=True).start()

if __name__ == "__main__":
    main()
