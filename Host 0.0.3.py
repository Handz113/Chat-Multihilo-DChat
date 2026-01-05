import socket
import threading
import json
import hashlib
import os
import ssl
import requests
from datetime import datetime
import time

# --- Configuración Inicial ---
usuarios_file = "usuarios.json"
historial_file = "historial.json"
pines_file = "pines.json"
salas_file = "salas.json"

# Configuración de OLLAMA
OLLAMA_URL = "http://localhost:11434/api/generate"
MODELO_IA = "llama3.2:3b"

# Verificación de certificados
if not (os.path.exists("server.crt") and os.path.exists("server.key")):
    print("⚠️ ADVERTENCIA: No se encontraron 'server.crt' o 'server.key'.")

# --- CACHÉ EN MEMORIA Y CONTROL DE CAMBIOS ---
usuarios_cache = {}
historial_cache = {}
pines_cache = {}
salas_nombres_cache = []
salas = {}
clientes = {}

# Banderas de cambios pendientes
cambios_pendientes = {
    "usuarios": False,
    "historial": False,
    "pines": False,
    "salas": False
}

# Lock para operaciones thread-safe
cache_lock = threading.Lock()

# --- INICIALIZACIÓN DE CACHÉ ---
def inicializar_cache():
    """Carga todos los datos en memoria al iniciar"""
    global usuarios_cache, historial_cache, pines_cache, salas_nombres_cache, salas
    
    # Cargar usuarios
    if os.path.exists(usuarios_file):
        try:
            with open(usuarios_file, "r") as f:
                usuarios_cache = json.load(f)
        except:
            usuarios_cache = {}
    else:
        usuarios_cache = {}
        guardar_cache_usuarios()
    
    # Cargar nombres de salas
    if os.path.exists(salas_file):
        try:
            with open(salas_file, "r") as f:
                salas_nombres_cache = json.load(f)
        except:
            salas_nombres_cache = ["General", "Equipo 1", "Equipo 2"]
    else:
        salas_nombres_cache = ["General", "Equipo 1", "Equipo 2"]
        guardar_cache_salas()
    
    # Inicializar estructura de salas
    salas = {nombre: [] for nombre in salas_nombres_cache}
    
    # Cargar historial
    if os.path.exists(historial_file):
        try:
            with open(historial_file, "r") as f:
                historial_cache = json.load(f)
        except:
            historial_cache = {s: [] for s in salas.keys()}
    else:
        historial_cache = {s: [] for s in salas.keys()}
        guardar_cache_historial()
    
    # Cargar pines
    if os.path.exists(pines_file):
        try:
            with open(pines_file, "r") as f:
                pines_cache = json.load(f)
        except:
            pines_cache = {s: "" for s in salas.keys()}
    else:
        pines_cache = {s: "" for s in salas.keys()}
        guardar_cache_pines()
    
    print("✅ Caché en memoria inicializado.")

# --- FUNCIONES DE GUARDADO A DISCO ---
def guardar_cache_usuarios():
    """Escribe el caché de usuarios a disco"""
    try:
        with open(usuarios_file, "w") as f:
            json.dump(usuarios_cache, f, indent=4)
    except Exception as e:
        print(f"Error guardando usuarios: {e}")

def guardar_cache_historial():
    """Escribe el caché de historial a disco"""
    try:
        with open(historial_file, "w") as f:
            json.dump(historial_cache, f, indent=4)
    except Exception as e:
        print(f"Error guardando historial: {e}")

def guardar_cache_pines():
    """Escribe el caché de pines a disco"""
    try:
        with open(pines_file, "w") as f:
            json.dump(pines_cache, f, indent=4)
    except Exception as e:
        print(f"Error guardando pines: {e}")

def guardar_cache_salas():
    """Escribe el caché de nombres de salas a disco"""
    try:
        with open(salas_file, "w") as f:
            json.dump(salas_nombres_cache, f, indent=4)
    except Exception as e:
        print(f"Error guardando salas: {e}")

# --- HILO AUTOSAVE ---
def hilo_autosave():
    """Hilo en segundo plano que guarda cambios cada 60 segundos"""
    while True:
        time.sleep(60)
        with cache_lock:
            if cambios_pendientes["usuarios"]:
                guardar_cache_usuarios()
                cambios_pendientes["usuarios"] = False
                print("💾 Usuarios guardados.")
            if cambios_pendientes["historial"]:
                guardar_cache_historial()
                cambios_pendientes["historial"] = False
                print("💾 Historial guardado.")
            if cambios_pendientes["pines"]:
                guardar_cache_pines()
                cambios_pendientes["pines"] = False
                print("💾 Pines guardados.")
            if cambios_pendientes["salas"]:
                guardar_cache_salas()
                cambios_pendientes["salas"] = False
                print("💾 Salas guardadas.")

# --- FUNCIONES DE ACCESO A USUARIOS ---
def cargar_usuarios():
    """Retorna el caché de usuarios"""
    with cache_lock:
        return usuarios_cache.copy()

def guardar_usuarios(data):
    """Modifica el caché y marca como pendiente de guardar"""
    with cache_lock:
        usuarios_cache.clear()
        usuarios_cache.update(data)
        cambios_pendientes["usuarios"] = True

# --- FUNCIONES DE GESTIÓN DE SALAS ---
def cargar_nombres_salas():
    """Retorna el caché de nombres de salas"""
    with cache_lock:
        return salas_nombres_cache.copy()

def guardar_nombres_salas(lista_nombres):
    """Modifica el caché de salas y marca como pendiente"""
    with cache_lock:
        salas_nombres_cache.clear()
        salas_nombres_cache.extend(lista_nombres)
        cambios_pendientes["salas"] = True

# --- FUNCIONES DE HISTORIAL ---
def cargar_historial():
    """Retorna el caché de historial"""
    with cache_lock:
        return {k: v.copy() for k, v in historial_cache.items()}

def registrar_mensaje_historial(sala, mensaje_formateado):
    """Registra mensaje en el caché sin escribir a disco inmediatamente"""
    if sala not in salas:
        return
    
    with cache_lock:
        if sala not in historial_cache:
            historial_cache[sala] = []
        
        historial_cache[sala].append(mensaje_formateado)
        
        # Limitar a 1000 mensajes por sala
        if len(historial_cache[sala]) > 1000:
            historial_cache[sala] = historial_cache[sala][-1000:]
        
        cambios_pendientes["historial"] = True

def enviar_historial_a_usuario(conn, sala):
    """Envía el historial del caché al usuario en un solo mensaje JSON"""
    with cache_lock:
        msgs = historial_cache.get(sala, [])
    
    if not msgs:
        return
    
    # Serializar lista de mensajes a JSON
    historial_json = json.dumps({
        "sala": sala,
        "mensajes": msgs,
        "total": len(msgs)
    })
    
    # Enviar en un solo mensaje con prefijo HISTORY_BATCH
    comando = f"HISTORY_BATCH:{historial_json}"
    enviar_privado(conn, comando)

# --- LÓGICA DE INTELIGENCIA ARTIFICIAL ---
def generar_resumen_ollama(sala):
    """Lee el historial del caché y solicita un resumen a Llama 3.2"""
    with cache_lock:
        mensajes = historial_cache.get(sala, [])
    
    if not mensajes:
        return "No hay suficientes mensajes para generar un resumen."
    
    ultimos_mensajes = mensajes[-20:]
    texto_conversacion = "\n".join(ultimos_mensajes)
    
    prompt_sistema = (
        f"Eres un asistente de secretaría técnica. Resume la siguiente conversación del chat de la sala '{sala}'. "
        "Ignora los mensajes de sistema como [ENTRÓ], [SALIÓ]. "
        "Enumera los puntos clave y decisiones. Sé breve y profesional en español."
    )
    
    payload = {
        "model": MODELO_IA,
        "prompt": f"{prompt_sistema}\n\nConversación:\n{texto_conversacion}",
        "stream": False,
        "keep_alive": 3600
    }
    
    try:
        print(f"🤖 [IA] Generando resumen para {sala}...")
        response = requests.post(OLLAMA_URL, json=payload, timeout=90)
        response.raise_for_status()
        resultado = response.json()
        return resultado.get("response", "La IA no devolvió respuesta.")
    except requests.exceptions.ConnectionError:
        return "❌ Error: El servicio de IA (Ollama) no está corriendo en el servidor."
    except Exception as e:
        return f"❌ Error generando resumen: {str(e)}"

# --- FUNCIONES DE PINES ---
def cargar_pines():
    """Retorna el caché de pines"""
    with cache_lock:
        return pines_cache.copy()

def guardar_pin(sala, mensaje):
    """Modifica el pin en el caché y marca como pendiente"""
    with cache_lock:
        pines_cache[sala] = mensaje
        cambios_pendientes["pines"] = True

def broadcast_pin(sala, mensaje):
    """Difunde actualización de pin a todos en la sala"""
    comando = f"PIN_UPDATE:{mensaje}"
    if sala in salas:
        for conn in salas[sala]:
            try:
                conn.send(comando.encode("utf-8"))
            except:
                pass

# --- Utilidades de Red ---
def broadcast(sala, mensaje, remitente_conn=None):
    """Difunde mensaje a todos en la sala"""
    hora = datetime.now().strftime("%H:%M")
    msg_final = f"[{hora}] {mensaje}"
    registrar_mensaje_historial(sala, msg_final)
    if sala not in salas:
        return
    for conn in list(salas[sala]):
        if conn != remitente_conn:
            try:
                conn.send(msg_final.encode("utf-8"))
            except:
                remover_cliente(conn)

def broadcast_lista_salas():
    """Difunde lista de salas a todos los clientes"""
    lista = list(salas.keys())
    json_salas = json.dumps(lista)
    msg = f"ROOMS_UPDATE:{json_salas}"
    for conn in clientes.keys():
        try:
            conn.send(msg.encode("utf-8"))
        except:
            pass

def enviar_privado(conn, mensaje):
    """Envía mensaje privado a un cliente"""
    try:
        conn.send(mensaje.encode("utf-8"))
    except:
        pass

def remover_cliente(conn):
    """Remueve cliente de todas las estructuras"""
    if conn in clientes:
        alias = clientes[conn]["alias"]
        sala = clientes[conn]["sala"]
        if sala in salas and conn in salas[sala]:
            salas[sala].remove(conn)
        del clientes[conn]
    try:
        conn.close()
    except:
        pass

# --- Auth ---
def registrar_usuario(conn, user, hashed_pwd, pregunta, hashed_resp):
    """Registra usuario en el caché"""
    with cache_lock:
        if user in usuarios_cache:
            conn.send("Usuario ya existe.\n".encode("utf-8"))
            return False
        
        rol_inicial = "estudiante"
        if len(usuarios_cache) == 0:
            rol_inicial = "admin"
        
        usuarios_cache[user] = {
            "pass": hashed_pwd,
            "rol": rol_inicial,
            "banned": False,
            "pregunta": pregunta,
            "resp_hash": hashed_resp
        }
        cambios_pendientes["usuarios"] = True
    
    conn.send(f"Registro exitoso. Rol asignado: {rol_inicial.upper()}.\n".encode("utf-8"))
    return True

def login_verificacion(user, hashed_pwd):
    """Verifica credenciales contra el caché"""
    with cache_lock:
        if user in usuarios_cache:
            datos = usuarios_cache[user]
            if datos["pass"] == hashed_pwd:
                if datos.get("banned", False):
                    return "BANNED"
                return datos.get("rol", "estudiante")
    return None

# --- Comandos ---
def procesar_comando(conn, mensaje, alias, rol, sala_actual):
    partes = mensaje.split(" ")
    comando = partes[0].lower()
    es_staff = (rol == "admin" or rol == "docente")
    es_admin = (rol == "admin")

    if comando == "/resume":
        enviar_privado(conn, "🤖 La IA está leyendo el historial... esto puede tardar unos segundos.")
        resumen = generar_resumen_ollama(sala_actual)
        enviar_privado(conn, f"\n✨ --- RESUMEN IA ({sala_actual}) --- ✨\n")
        enviar_privado(conn, resumen)
        enviar_privado(conn, "\n----------------------------------------\n")
        return True

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
        with cache_lock:
            salas_nombres_cache.append(nombre_sala)
            if nombre_sala not in pines_cache:
                pines_cache[nombre_sala] = ""
            if nombre_sala not in historial_cache:
                historial_cache[nombre_sala] = []
            cambios_pendientes["salas"] = True
            cambios_pendientes["pines"] = True
            cambios_pendientes["historial"] = True
        broadcast_lista_salas()
        enviar_privado(conn, f"✅ Sala '{nombre_sala}' creada.")
        return True

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
        if sala_destino == nombre_sala:
            sala_destino = list(salas.keys())[1]
        
        usuarios_afectados = list(salas[nombre_sala])
        for c in usuarios_afectados:
            salas[nombre_sala].remove(c)
            salas[sala_destino].append(c)
            clientes[c]["sala"] = sala_destino
            enviar_privado(c, f"⚠️ La sala actual fue eliminada. Movido a {sala_destino}.")
            enviar_historial_a_usuario(c, sala_destino)
        del salas[nombre_sala]
        with cache_lock:
            salas_nombres_cache.remove(nombre_sala)
            if nombre_sala in pines_cache:
                del pines_cache[nombre_sala]
            if nombre_sala in historial_cache:
                del historial_cache[nombre_sala]
            cambios_pendientes["salas"] = True
            cambios_pendientes["pines"] = True
            cambios_pendientes["historial"] = True
        broadcast_lista_salas()
        enviar_privado(conn, f"✅ Sala '{nombre_sala}' eliminada.")
        return True

    if comando == "/get_users":
        lista_equipos = {s: [] for s in salas.keys()}
        for c, datos in clientes.items():
            s_u = datos["sala"]
            if s_u in lista_equipos:
                info = f"{datos['alias']}"
                if datos['rol'] != "estudiante":
                    info += f" [{datos['rol'].upper()}]"
                if datos['muted']:
                    info += " 🔇"
                lista_equipos[s_u].append(info)
        enviar_privado(conn, f"USERS_LIST:{json.dumps(lista_equipos)}")
        return True


    if comando == "/mirol":
        enviar_privado(conn, f"🕵️ Tu rol es: [{rol.upper()}]")
        return True

    if comando == "/join":
        nueva_sala = " ".join(partes[1:]) if len(partes) > 1 else ""
        if nueva_sala in salas:
            if conn in salas[sala_actual]:
                salas[sala_actual].remove(conn)
            salas[nueva_sala].append(conn)
            clientes[conn]["sala"] = nueva_sala
            enviar_privado(conn, f"[SISTEMA] Entraste a: {nueva_sala}")
            enviar_historial_a_usuario(conn, nueva_sala)
            with cache_lock:
                pin = pines_cache.get(nueva_sala, "")
            conn.send(f"PIN_UPDATE:{pin}".encode("utf-8"))
        else:
            enviar_privado(conn, f"[SISTEMA] Sala no existe.")
        return True

    if comando == "/pin":
        if not es_staff:
            return True
        texto = " ".join(partes[1:])
        if not texto:
            return True
        with cache_lock:
            actual = pines_cache.get(sala_actual, "")
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
        if not es_staff:
            return True
        broadcast(sala_actual, f"\n📢 [ANUNCIO] 📢\n{' '.join(partes[1:])}\n")
        return True
    
    if comando == "/unpin":
        if not es_staff:
            return True
        
        # Verificar si hay un pin que borrar
        with cache_lock:
            actual = pines_cache.get(sala_actual, "")
            
        if not actual:
            enviar_privado(conn, "ℹ️ No hay ningún mensaje fijado en esta sala.")
            return True

        # Borrar pin (string vacío)
        guardar_pin(sala_actual, "")
        broadcast_pin(sala_actual, "")
        enviar_privado(conn, "✅ Mensaje fijado eliminado.")
        return True
        
    if comando == "/help":
        ayuda = "--- AYUDA ---\n/mirol, /join [sala], /resume (IA)"
        if es_staff:
            ayuda += "\n(STAFF) /kick, /mute, /unmute, /anuncio, /pin, /unpin"
        if es_admin:
            # Agregamos /roles aquí
            ayuda += "\n(ADMIN) /crear, /borrar, /promote, /ban, /unban, /roles" 
        enviar_privado(conn, ayuda)
        return True

    if comando == "/kick":
        if not es_staff:
            return True
        target = partes[1].lower() if len(partes) > 1 else ""
        for s, d in list(clientes.items()):
            if d["alias"].lower() == target:
                if d["rol"] == "admin":
                    return True
                enviar_privado(s, "🚫 Expulsado.")
                remover_cliente(s)
                enviar_privado(conn, f"✅ {target} expulsado.")
                return True
        return True
        
    if comando == "/roles":
        if not es_admin:
            return True # Ignorar si no es admin
            
        mensaje_roles = (
            "📋 --- ROLES DISPONIBLES ---\n"
            "Estos son los roles válidos para /promote:\n\n"
            "• admin      (Control total)\n"
            "• docente    (Moderación: kick, ban, mute, pin)\n"
            "• estudiante (Rol por defecto)\n\n"
            "Ejemplo de uso: /promote Juan docente"
        )
        enviar_privado(conn, mensaje_roles)
        return True

    if comando == "/ban":
        if not es_staff:
            return True
        target = partes[1] if len(partes) > 1 else ""
        with cache_lock:
            usrs = usuarios_cache.copy()
        if target in usrs:
            if usrs[target]["rol"] == "admin":
                return True
            usrs[target]["banned"] = True
            guardar_usuarios(usrs)
            for s, d in list(clientes.items()):
                if d["alias"] == target:
                    enviar_privado(s, "⛔ BANEADO.")
                    remover_cliente(s)
            enviar_privado(conn, "✅ Usuario baneado.")
        return True

    if comando == "/unban":
        if not es_admin:
            return True
        target = partes[1] if len(partes) > 1 else ""
        with cache_lock:
            usrs = usuarios_cache.copy()
        if target in usrs:
            usrs[target]["banned"] = False
            guardar_usuarios(usrs)
            enviar_privado(conn, "✅ Desbaneado.")
        return True
    
    if comando == "/mute":
        if not es_staff:
            return True
        target = partes[1].lower() if len(partes) > 1 else ""
        for s, d in clientes.items():
            if d["alias"].lower() == target:
                d["muted"] = True
                enviar_privado(s, "😶 Silenciado.")
                enviar_privado(conn, "✅ Listo.")
                return True
        return True

    if comando == "/unmute":
        if not es_staff:
            return True
        target = partes[1].lower() if len(partes) > 1 else ""
        for s, d in clientes.items():
            if d["alias"].lower() == target:
                d["muted"] = False
                enviar_privado(s, "🗣️ Liberado.")
                enviar_privado(conn, "✅ Listo.")
                return True
        return True

    if comando == "/promote":
        if not es_admin:
            return True
        if len(partes) < 3:
            return True
        target, n_rol = partes[1], partes[2].lower()
        with cache_lock:
            usrs = usuarios_cache.copy()
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
                conn.send(f"Bienvenido {user} [{rol.upper()}]\n".encode())
                
                sala_inicial = list(salas.keys())[0]
                clientes[conn] = {"alias": user, "sala": sala_inicial, "rol": rol, "muted": False, "pending_pin": None}
                salas[sala_inicial].append(conn)
                
                broadcast(sala_inicial, f"[SISTEMA] {user} entró.", conn)
                
                json_salas = json.dumps(list(salas.keys()))
                conn.send(f"ROOMS_UPDATE:{json_salas}".encode("utf-8"))
                
                enviar_historial_a_usuario(conn, sala_inicial)
                with cache_lock:
                    pin = pines_cache.get(sala_inicial, "")
                conn.send(f"PIN_UPDATE:{pin}".encode("utf-8"))

                while True:
                    data = conn.recv(1024).decode().strip()
                    if not data:
                        break
                    
                    if conn in clientes:
                        rol = clientes[conn]["rol"]

                    if clientes[conn].get("pending_pin"):
                        if data.lower() in ["y", "s", "si"]:
                            guardar_pin(clientes[conn]["sala"], clientes[conn]["pending_pin"])
                            broadcast_pin(clientes[conn]["sala"], clientes[conn]["pending_pin"])
                            enviar_privado(conn, "✅ Actualizado.")
                        else:
                            enviar_privado(conn, "❌ Cancelado.")
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
                        if rol == "admin":
                            prefijo = "👑 [ADMIN] "
                        elif rol == "docente":
                            prefijo = "🎓 [DOCENTE] "
                        broadcast(clientes[conn]["sala"], f"{prefijo}{user}: {data}", conn)
                return
            else:
                conn.send("Error credenciales.".encode())
                return
        
        elif opcion == "r":
            conn.send("ACK".encode())
            u = conn.recv(1024).decode().strip()
            conn.send("ACK".encode())
            p = conn.recv(1024).decode().strip()
            conn.send("ACK".encode())
            q = conn.recv(1024).decode().strip()
            conn.send("ACK".encode())
            r = conn.recv(1024).decode().strip().lower()
            registrar_usuario(conn, u, hashlib.sha256(p.encode()).hexdigest(), q, hashlib.sha256(r.encode()).hexdigest())
        elif opcion == "rec_req":
            conn.send("ACK".encode())
            u = conn.recv(1024).decode().strip()
            with cache_lock:
                usrs = usuarios_cache.copy()
            conn.send(f"PREGUNTA:{usrs[u]['pregunta']}".encode() if u in usrs else "ERROR".encode())
        elif opcion == "rec_reset":
            conn.send("ACK".encode())
            u = conn.recv(1024).decode().strip()
            conn.send("ACK".encode())
            r = conn.recv(1024).decode().strip().lower()
            conn.send("ACK".encode())
            np = conn.recv(1024).decode().strip()
            with cache_lock:
                usrs = usuarios_cache.copy()
            if u in usrs and usrs[u]["resp_hash"] == hashlib.sha256(r.encode()).hexdigest():
                usrs[u]["pass"] = hashlib.sha256(np.encode()).hexdigest()
                guardar_usuarios(usrs)
                conn.send("EXITO".encode())
            else:
                conn.send("ERROR".encode())
    except:
        pass
    finally:
        remover_cliente(conn)

def main():
    # Inicializar caché en memoria
    inicializar_cache()
    
    # Iniciar hilo autosave
    autosave_thread = threading.Thread(target=hilo_autosave, daemon=True)
    autosave_thread.start()
    print("💾 [AUTOSAVE] Hilo de guardado automático iniciado.")
    
    # Verificación de IA
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
    s.bind(("192.168.1.100", 5000))
    s.listen(5)
    print("📌 [SERVIDOR COMPLETO] Listo en puerto 5000.")
    
    try:
        while True:
            c, a = s.accept()
            threading.Thread(target=manejar_cliente, args=(ctx.wrap_socket(c, server_side=True), a), daemon=True).start()
    except KeyboardInterrupt:
        print("\n⚠️ Guardando cambios pendientes antes de cerrar...")
        with cache_lock:
            if cambios_pendientes["usuarios"]:
                guardar_cache_usuarios()
            if cambios_pendientes["historial"]:
                guardar_cache_historial()
            if cambios_pendientes["pines"]:
                guardar_cache_pines()
            if cambios_pendientes["salas"]:
                guardar_cache_salas()
        print("✅ Servidor cerrado correctamente.")

if __name__ == "__main__":
    main()
