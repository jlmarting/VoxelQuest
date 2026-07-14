#!/usr/bin/env python3
import http.server
import socketserver
import webbrowser
import os
import socket

PORT = 9000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

class ReuseTCPServer(socketserver.TCPServer):
    allow_reuse_address = True
    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        super().server_bind()

def main():
    with ReuseTCPServer(("", PORT), Handler) as httpd:
        print(f"Servidor iniciado en http://localhost:{PORT}")
        print("Presiona Ctrl+C para detener")

        # Open browser
        webbrowser.open(f"http://localhost:{PORT}")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor detenido")

if __name__ == "__main__":
    main()
