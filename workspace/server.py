import http.server
import socketserver
import threading

PORT = 8080

Handler = http.server.SimpleHTTPRequestHandler

def start_server():
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"服务器启动在端口 {PORT}")
        print(f"请访问: http://localhost:{PORT}/login_page.html")
        httpd.serve_forever()

if __name__ == "__main__":
    server_thread = threading.Thread(target=start_server)
    server_thread.daemon = True
    server_thread.start()
    
    # 保持主线程运行
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("\n服务器停止")