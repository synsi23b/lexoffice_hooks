from flask import Flask,request,json, Response
import requests
from dotenv import load_dotenv
import os
from pathlib import Path
import subprocess
from worker import Worker
from lexoffice import create_subscriptions
import base64
from logging.config import dictConfig
import logging


dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {
        'wsgi': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://flask.logging.wsgi_errors_stream',
            'formatter': 'default'
        },
        'file_handler': {
            'level': 'INFO',
            'formatter': 'default',
            'class': 'logging.FileHandler',
            'filename': 'hooking.log',
            'mode': 'a',
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi', 'file_handler']
    }
})


def download_pubkey():
    uri = "https://developers.lexoffice.io/webhookSignature/public/public_key.pub"
    path = Path(__file__).parent.resolve() / "public_key.pub"
    if path.exists():
        path.unlink()
    response = requests.get(uri)
    with open(path, 'wb') as f:
        f.write(response.content)
    

def verify_sig():
    here = Path(__file__).parent.resolve()
    if request.content_length < 10000:
        data = here / "request.json"
        with open(data, "wb") as f:
            f.write(request.get_data())
        sig = request.headers.get("X-Lxo-Signature", "")
        sigout = here / "signature_decoded"
        with open(sigout, "wb") as f:
            f.write(base64.b64decode(sig))
        res = subprocess.call(["openssl", "dgst", "-verify", str(here / "public_key.pub"), "-signature", str(sigout), str(data)])
        return res == 0
    return False


wrk = Worker()
app = Flask("lexhooks")


@app.route('/lexhook/voucher/created', methods=['POST', 'HEAD'])
def lex_cb():
    if verify_sig():
        #return Response(status=200)
        logging.info("Signature verified")
    else:
        logging.info("Error verifing signature of the call")
        #return Response(status=400)
    jdata = request.get_json()
    wrk.put(jdata)
    return Response(status=200)
    

download_pubkey()
create_subscriptions(os.getenv("callback_base_url") + "/lexhook")


if __name__ == '__main__':
    #download_pubkey()
    #create_subscriptions()
    app.run(debug=False, host="0.0.0.0")
    wrk.stop()