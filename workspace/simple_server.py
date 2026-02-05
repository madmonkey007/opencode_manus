import http.server
import socketserver
import os

PORT = 8080

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.path = '/login_page.html'
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

os.chdir('/workspace')

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"服务器启动在端口 {PORT}")
    print(f"打开浏览器访问: http://localhost:{PORT}")
    httpd.serve_forever()