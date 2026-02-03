from livereload import Server
server = Server()
server.watch('frontend.html')
server.serve(port=5500)