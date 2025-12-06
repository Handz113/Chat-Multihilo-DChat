from chat_app import ChatApp

# Este archivo es el punto de entrada.
# Su única responsabilidad es crear y
# ejecutar la aplicación principal.

if __name__ == "__main__":
    app = ChatApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
