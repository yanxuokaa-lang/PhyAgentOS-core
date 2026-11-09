#!/usr/bin/env python3
"""Local HTTP contract check with an explicitly identified CPU engine double."""
import json
from pathlib import Path
import threading
import urllib.request
import urllib.error
from http.server import HTTPServer
from serve_decisions import server_class


class Engine:
    def __init__(self):self.calls=0
    def predict(self,payload):
        self.calls+=1
        return {'execution':{'forward_passes':1,'autoregressive_decode_steps':0,'network_model_calls':0},
                'states':[{'id':s['id'],'answers':{}} for s in payload['states']]}


def main():
    engine=Engine();server=HTTPServer(('127.0.0.1',0),server_class(engine,Path('web').resolve()))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    def request(path,data=None):
        req=urllib.request.Request(base+path,data=json.dumps(data).encode() if data is not None else None,
                                   headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req) as r:return r.status,r.read()
        except urllib.error.HTTPError as exc:return exc.code,exc.read()
    try:
        payload={'states':[{'id':'a','state':'A','questions':{'q':{'type':'boolean','instructions':'Is A present?'}}}]}
        assert request('/api/health')[0]==200
        assert request('/')[0]==200
        assert request('/../.env')[0]==404
        assert request('/api/evaluate',payload)[0]==200
        assert request('/api/evaluate',{'states':[]})[0]==400
        assert engine.calls==1
    finally:server.shutdown();server.server_close()
    result={'status':'passed','checks':['health','static page','path traversal rejected','valid inference routing','invalid schema rejected before engine'],
            'engine':'explicit CPU test double; not GPU inference','engine_calls':engine.calls}
    Path('research/server_contract_check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
