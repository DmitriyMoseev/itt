import cgi
import re
import io
from http.client import HTTPSConnection
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
            text = text.replace('https://habrahabr.ru',
                                'http://localhost:8000')

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
        response = self.request_habr(self.path)

        self.send_response(response.status)
        self.send_headers(response.headers)
        self.send_body(response.read(), response.headers['Content-Type'])

    def request_habr(self, path):
        conn = HTTPSConnection('habrahabr.ru')
        conn.request('GET', path)
        return conn.getresponse()

    def send_headers(self, headers):
        propagating_headers = {'Location', 'Content-Type'}
        for key in propagating_headers:
            if key in headers:
                self.send_header(key, headers[key])
        self.end_headers()

    def send_body(self, data, content_type):
        type_, params = cgi.parse_header(content_type)

        if type_ == 'text/html':
            data = HTMLConverter().convert(data, params['charset'])

        self.wfile.write(data)


def run(server_class=HTTPServer):
    httpd = server_class(('', 8000), HTTPRequestHandler)
    httpd.serve_forever()


if __name__ == '__main__':
    run()
