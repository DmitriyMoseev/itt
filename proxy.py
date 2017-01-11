#!/usr/bin/env python3
import cgi
import re
import io
from argparse import ArgumentParser
from http.client import HTTPSConnection, HTTPConnection
from http.server import HTTPServer, BaseHTTPRequestHandler
from html.parser import HTMLParser


class HTMLConverter(HTMLParser):

    def __init__(self):
        self.immutable_tags = {'script', 'style'}
        self.inside_immutable_tag = False
        self.out = io.StringIO()
        super().__init__(convert_charrefs=False)

    def convert(self, html, charset):
        self.feed(html.decode(charset))
        return self.out.getvalue().encode(charset)

    def handle_starttag(self, tag, attrs):
        if tag in self.immutable_tags:
            self.inside_immutable_tag = True

        text = self.get_starttag_text()
        if tag == 'a':
            text = text.replace(settings.target_url, settings.proxy_url)

        self.out.write(text)

    def handle_endtag(self, tag):
        if tag in self.immutable_tags:
            self.inside_immutable_tag = False

        self.out.write('</{0}>'.format(tag))

    def handle_data(self, data):
        if not self.inside_immutable_tag:
            data = re.sub(r'\b(\w{6})\b', r'\1&trade;', data)

        self.out.write(data)

    def handle_startendtag(self, tag, attrs):
        self.out.write(self.get_starttag_text())

    def handle_comment(self, data):
        self.out.write('<!--{0}-->'.format(data))

    def handle_decl(self, decl):
        self.out.write('<!{0}>'.format(decl))

    def handle_charref(self, name):
        self.out.write('&#{0};'.format(name))

    def handle_entityref(self, name):
        self.out.write('&{0};'.format(name))


class HTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        response = self.request_target(self.path)

        self.send_response(response.status)
        self.send_headers(response.headers)
        self.send_body(response.read(), response.headers['Content-Type'])

    def request_target(self, path):
        if settings.target_protocol == 'https':
            connection_class = HTTPSConnection
        else:
            connection_class = HTTPConnection
        conn = connection_class(settings.target_host)
        conn.request('GET', path)
        return conn.getresponse()

    def send_headers(self, headers):
        location = headers['Location']
        if location:
            location = location.replace(settings.target_url,
                                        settings.proxy_url)
            self.send_header('Location', location)

        content_type = headers['Content-Type']
        if content_type:
            self.send_header('Content-Type', content_type)

        self.end_headers()

    def send_body(self, data, content_type):
        type_, params = cgi.parse_header(content_type)

        if type_ == 'text/html':
            charset = params.get('charset', 'utf-8')
            data = HTMLConverter().convert(data, charset)

        self.wfile.write(data)


class Settings:
    def __init__(self):
        self.parse_args()

        self.proxy_url = 'http://{0}:{1}'.format(self.host, self.port)
        self.target_url = '{0}://{1}'.format(self.target_protocol,
                                             self.target_host)

    def parse_args(self):
        parser = ArgumentParser()
        parser.add_argument('--host', default='localhost')
        parser.add_argument('--port', type=int, default=8000)
        parser.add_argument('--target-host', default='habrahabr.ru')
        parser.add_argument('--target-protocol',
                            default='https', choices=['https', 'http'])
        return parser.parse_args(namespace=self)


if __name__ == '__main__':
    settings = Settings()
    httpd = HTTPServer((settings.host, settings.port), HTTPRequestHandler)
    httpd.serve_forever()
