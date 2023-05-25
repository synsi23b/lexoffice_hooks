from flask import Flask,request,json, Response
import requests
from dotenv import load_dotenv
import os
from pathlib import Path
import subprocess
from worker import Worker


load_dotenv()


def delete_old_subscriptions():
    endpoint = "https://api.lexoffice.io/v1/event-subscriptions"
    headers = {
        'Authorization': f"Bearer {os.getenv('lexoffice_apkikey')}",
        'Accept': 'application/json',
    }
    response = requests.get(endpoint, headers=headers)
    subs = response.json()
    print(subs)
    for sub in subs.get("content", []):
        id = sub["subscriptionId"]
        response = requests.delete(f"{endpoint}/{id}", headers=headers)
        print(f"Delete: {sub['eventType']} - {id} -> Code: {response.status_code}")


def create_subscriptions():
    delete_old_subscriptions()
    endpoint = "https://api.lexoffice.io/v1/event-subscriptions"
    headers = {
        'Authorization': f"Bearer {os.getenv('lexoffice_apkikey')}",
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    data = {
        "eventType": "voucher.created",
        "callbackUrl": f"https://{os.getenv('callback_base_url')}/lexhook/voucher/created"
    }
    response = requests.post(endpoint, headers=headers, json=data)
    if response.status_code != 201:
        print(f"error creating event! code {response.status_code}")


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
        with open(sigin, "wb") as f:
            f.write(bytes(sig, "utf-8"))
        sigout = here / "signature_decoded"
        subprocess.call(["openssl", "base64", "-d", "-in", str(sigin), "-out", str(sigout)])
        res = subprocess.call(["openssl", "dgst", "-verify", str(here / "public_key.pub"), "-signature", str(sigout), str(data)])
        return res == 0
    return False


download_pubkey()
create_subscriptions()
wrk = Worker()
app = Flask("lexhooks")


@app.route('/lexhook/voucher/created/', methods=['POST'])
def voucher_created():
    if verify_sig():
        #return Response(status=200)
        print("Signature verified")
    else:
        print("Error verifing signature of the call")
        #return Response(status=400)
    jdata = request.get_json()
    wrk.put(jdata)
    return Response(status=200)
    

if __name__ == '__main__':
    #download_pubkey()
    #create_subscriptions()
    app.run(debug=True)