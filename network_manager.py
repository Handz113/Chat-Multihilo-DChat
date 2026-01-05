import socket, threading, queue, ssl

class NetworkManager:
    def __init__(self, message_queue):
        self.client = None; self.connected = False; self.queue = message_queue
        self.host = "192.168.100.37"; self.port = 5000

    def connect(self):
        if self.connected: return (True, "OK")
        try:
            ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
            raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM); raw.settimeout(5)
            self.client = ctx.wrap_socket(raw, server_hostname=self.host)
            self.client.connect((self.host, self.port)); self.connected = True; self.client.settimeout(None)
            return (True, "OK")
        except Exception as e: return (False, str(e))

    def disconnect(self):
        self.connected = False
        try: self.client.close()
        except: pass

    def send_msg(self, msg):
        if self.connected:
            try: 
                self.client.send(msg.encode("utf-8"))
                return True
            except (ssl.SSLEOFError, BrokenPipeError, OSError): 
                self.disconnect()
                return False
        return False

    def start_listening(self):
        threading.Thread(target=self._listen, daemon=True).start()

    def _listen(self):
        """Hilo que escucha mensajes del servidor"""
        while self.connected:
            try:
                data = self.client.recv(65536).decode("utf-8")
                if not data: 
                    break
                self.queue.put(data)
            except ssl.SSLEOFError:
                # El servidor cerró la conexión SSL (comportamiento esperado al salir/kick)
                break 
            except OSError:
                # El socket murió
                break
            except Exception as e:
                print(f"Error desconocido en listen: {e}")
                break
        
        self.connected = False
        self.queue.put("[SISTEMA] Desconectado.")

    def solicitar_usuarios(self): self.send_msg("/get_users")

    # Auth Methods
    # En network_manager.py

    def login(self, u, p):
        # Si no estamos conectados, intentamos conectar primero
        if not self.connected: 
            exito, error = self.connect()
            if not exito: 
                self.queue.put(f"[LOGIN] Error de conexión: {error}")
                return

        try:
            self.client.send("l".encode())
            ack = self.client.recv(1024) # Esperar ACK inicial
            
            self.client.send(u.encode())
            self.client.recv(1024) # ACK usuario
            
            self.client.send(p.encode())
            resp = self.client.recv(1024).decode().strip()
            
            self.queue.put(f"[LOGIN] {resp}")
            
            # --- CORRECCIÓN CRÍTICA ---
            # Si el servidor no responde con "Bienvenido", significa que rechazó el login
            # y cerró el socket en su 'finally'. Debemos cerrar aquí también.
            if "Bienvenido" not in resp:
                self.disconnect()
                
        except Exception as e: 
            self.disconnect()
            self.queue.put(f"[LOGIN] Error de red: {str(e)}")

    def register(self, u, p, q, a):
        if not self.connected: 
            exito, error = self.connect()
            if not exito: 
                self.queue.put(f"[REGISTRO] Error de conexión: {error}")
                return

        try:
            self.client.send("r".encode())
            self.client.recv(1024)
            
            self.client.send(u.encode())
            self.client.recv(1024)
            
            self.client.send(p.encode())
            self.client.recv(1024)
            
            self.client.send(q.encode())
            self.client.recv(1024)
            
            self.client.send(a.encode())
            resp = self.client.recv(1024).decode()
            
            self.queue.put(f"[REGISTRO] {resp}")
            
            # --- CORRECCIÓN CRÍTICA ---
            # El servidor SIEMPRE cierra la conexión tras el registro.
            # Debemos desconectar el cliente para limpiar el socket.
            self.disconnect() 
            
        except Exception as e: 
            self.disconnect()
            self.queue.put(f"[REGISTRO] Error de red: {str(e)}")

    def recover_step1(self, u):
        if not self.connected: self.connect()
        try:
            self.client.send("rec_req".encode()); self.client.recv(1024)
            self.client.send(u.encode()); self.queue.put(f"[RECUPERACION_DATA] {self.client.recv(1024).decode()}")
        except: self.disconnect()

    def recover_step2(self, u, r, np):
        if not self.connected: self.connect()
        try:
            self.client.send("rec_reset".encode()); self.client.recv(1024); self.client.send(u.encode())
            self.client.recv(1024); self.client.send(r.encode()); self.client.recv(1024)
            self.client.send(np.encode()); self.queue.put(f"[RECUPERACION_RESULT] {self.client.recv(1024).decode()}")
        except: self.disconnect()
