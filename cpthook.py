from flask import Flask,request,json, Response
import requests
from dotenv import load_dotenv
import os
from pathlib import Path
import subprocess
from worker import Worker
from lexoffice import create_subscriptions


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
        sigin = here / "signature_base64"
        with open(sigin, "w") as f:
            f.write(sig)
        sigout = here / "signature_decoded"
        subprocess.call(["openssl", "base64", "-d", "-in", str(sigin), "-out", str(sigout)])
        res = subprocess.call(["openssl", "dgst", "-verify", str(here / "public_key.pub"), "-signature", str(sigout), str(data)])
        return res == 0
    return False


wrk = Worker()
app = Flask("lexhooks")


@app.route('/lexhook/voucher/created', methods=['POST', 'HEAD'])
def lex_cb():
    if verify_sig():
        #return Response(status=200)
        print("Signature verified")
    else:
        print("Error verifing signature of the call")
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