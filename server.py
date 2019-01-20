#  coding: utf-8 
import socketserver
from http import HTTPStatus
import html
import os

# Copyright 2013 Abram Hindle, Eddie Antonio Santos
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
# Furthermore it is derived from the Python documentation examples thus
# some of the code is Copyright © 2001-2013 Python Software
# Foundation; All Rights Reserved
#
# http://docs.python.org/2/library/socketserver.html
#
# run: python freetests.py

# try: curl -v -X GET http://127.0.0.1:8080/

# Default error message template
DEFAULT_ERROR_MESSAGE = """\
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
        "http://www.w3.org/TR/html4/strict.dtd">
<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html;charset=utf-8">
        <title>Error response</title>
    </head>
    <body>
        <h1>Error response</h1>
        <p>Error code: %(code)d</p>
        <p>Message: %(message)s.</p>
    </body>
</html>
"""

DEFAULT_ERROR_CONTENT_TYPE = "text/html;charset=utf-8"
DEFAULT_OK_CONTENT_TYPE = "text/%(type)s;charset=utf-8"

class HttpError:

    def __init__(self, httpStatus, custom_discription):
        self.httpStatus = httpStatus
        self.custom_discription = custom_discription


class MyWebServer(socketserver.BaseRequestHandler):
    # https://github.com/python/cpython/blob/3.7/Lib/http/server.py
    
    def handle(self):
        self.data = self.request.recv(1024).strip()
        # print("Got a request of: %s\n" % self.data)
        command, path, error = self._parse_request()
        if(error != None):
            response = self._send_error(error)
            # print("response", response)
        else: # error == None
            response = self._parse_path(path)    
            # print("response", response)   
        
        self.request.sendall(response)


    def _parse_path(self, path):
        static_file_path = os.path.abspath("www")
        # get the path we need
        des_path = static_file_path + path
        
        if(os.path.isfile(des_path)):
            # print("des_path", des_path)

            file_type = des_path.split("/")[-1].split(".")[-1]
            # print(file_type)
            if(file_type == "css" or file_type == "html"):
                response = self._send_body(des_path, file_type, HTTPStatus.OK)
            else:
                response = self._send_error(HttpError(HTTPStatus.NOT_FOUND, "only serve css & html file"))
        
        elif(os.path.isdir(des_path)): # we have this dir
            if(des_path.endswith("/") and os.path.isfile(des_path+"index.html")):
                response = self._send_body(des_path+"index.html", "html", HTTPStatus.OK)

            elif(not des_path.endswith("/") and os.path.isfile(des_path+"/"+"index.html")):
                response = self._send_redirect(path+"/", HTTPStatus.MOVED_PERMANENTLY) 

            else:
                response = self._send_error(HttpError(HTTPStatus.NOT_FOUND, "We have this dir but don't have index.html"))

        else:
            response = self._send_error(HttpError(HTTPStatus.NOT_FOUND, "Not found the path"))

        return response


    def _send_redirect(self, redirect_path, http_status):
        status = "HTTP/1.1 {} {}\r\n".format(http_status.value, http_status.phrase).encode('latin-1', 'strict')

        header = []
        header.append(status)
        header.append(self._get_header("Location", redirect_path))
        header.append(b"\r\n")

        response = header

        return b"".join(response)


    def _send_body(self, des_path, file_type, http_status):
        with open(des_path, 'r') as content_file:
            content = content_file.read()
        body = content.encode('UTF-8', 'replace')


        status = "HTTP/1.1 {} {}\r\n".format(http_status.value, http_status.phrase).encode('latin-1', 'strict')

        header = []
        header.append(status)
        header.append(self._get_header("Content-Type", (DEFAULT_OK_CONTENT_TYPE % {"type": file_type})))
        header.append(self._get_header("Content-Length", str(len(body))))
        header.append(b"\r\n")

        response = header + [body]

        return b"".join(response)


    def _get_header(self, key, value):
        return ("%s: %s\r\n" % (key, value)).encode('latin-1', 'strict')


    def _send_error(self, error):
        content = (DEFAULT_ERROR_MESSAGE % {
                'code': error.httpStatus,
                'message': html.escape(error.custom_discription, quote=False)
            })
        body = content.encode('UTF-8', 'replace')
        # print("body", body)
        status = "HTTP/1.1 {} {}\r\n".format(error.httpStatus.value, error.httpStatus.phrase)

        header = []
        header.append(status.encode('latin-1', 'strict'))
        header.append(self._get_header("Content-Type", DEFAULT_ERROR_CONTENT_TYPE))
        header.append(self._get_header("Content-Length", str(len(body))))
        header.append(b"\r\n")

        response = header + [body]

        return b"".join(response)


    def _parse_request(self):
        error = None # the flag indicate the function error
        command = None
        path = None
        
        requestline = str(self.data, 'iso-8859-1')
        requestline = requestline.rstrip('\r\n')
        words = requestline.split()
        # print(words)

        if(len(words) >= 3):
            version = words[2] # check the version
            if(version != 'HTTP/1.1'):
                error = HttpError(HTTPStatus.BAD_REQUEST, "Only serve for HTTP 1.1")
                return (command, path, error)

            command = words[0]
            if(command in ['GET', 'POST', 'PUT', 'DELETE']):
                if(command == 'GET'):
                    return (command, words[1], error)
                else:
                    error = HttpError(HTTPStatus.METHOD_NOT_ALLOWED, "Only serve for GET Method")
                    return (command, path, error)
            else:
                error = HttpError(HTTPStatus.BAD_REQUEST, "The method not in ['GET', 'POST', 'PUT', 'DELETE']")
                return (command, path, error)

        else: # len(words) < 3
            error = HttpError(HTTPStatus.BAD_REQUEST, "<command> <path> <version> is not complete")
            return (command, path, error)



if __name__ == "__main__":
    HOST, PORT = "localhost", 8080

    socketserver.TCPServer.allow_reuse_address = True
    # Create the server, binding to localhost on port 8080
    server = socketserver.TCPServer((HOST, PORT), MyWebServer)

    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server.serve_forever()