"""LOCALHOST-ONLY JSON HTTP reference transport. DO NOT expose on Internet.
No TLS, persistence of replay counters, rate-limiting or production identities here.
"""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import json
from urllib.parse import unquote
from .orchestrator import AdmissionError

MAX_BODY_BYTES=1_048_576

def handler_for(orchestrator):
    class Handler(BaseHTTPRequestHandler):
        def _reply(self,code,obj):
            raw=json.dumps(obj,sort_keys=True).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(raw)))
            self.end_headers();self.wfile.write(raw)
        def do_POST(self):
            try:
                length=int(self.headers.get('Content-Length','-1'))
                if length<0 or length>MAX_BODY_BYTES: return self._reply(413,{'error':'body_size'})
                obj=json.loads(self.rfile.read(length))
                if self.path=='/v1/handshake':return self._reply(200,orchestrator.handshake(obj['agent_id']))
                if self.path=='/v1/observations':return self._reply(202,orchestrator.admit(obj))
                return self._reply(404,{'error':'not_found'})
            except AdmissionError as e:self._reply(403,{'error':str(e)})
            except (ValueError,KeyError,TypeError,json.JSONDecodeError):self._reply(400,{'error':'bad_request'})
        def do_GET(self):
            if self.path.startswith('/v1/scenes/'):
                return self._reply(200,orchestrator.snapshot(unquote(self.path[len('/v1/scenes/'):])))
            return self._reply(404,{'error':'not_found'})
        def log_message(self,fmt,*args):pass
    return Handler

def create_local_server(orchestrator,port=0):
    return ThreadingHTTPServer(('127.0.0.1',port),handler_for(orchestrator))
