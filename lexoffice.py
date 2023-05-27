import requests
from dotenv import load_dotenv
import os
from pathlib import Path


load_dotenv()
here = Path(__file__).parent.resolve()


resourceurl = "https://api.lexoffice.io/v1"
base_header = {
        'Authorization': f"Bearer {os.getenv('lexoffice_apkikey')}",
        'Accept': 'application/json',
    }


def delete_old_subscriptions():
    endpoint = resourceurl + "/event-subscriptions"
    response = requests.get(endpoint, headers=base_header)
    subs = response.json()
    print(f"current subs callback result: {subs}")
    for sub in subs.get("content", []):
        id = sub["subscriptionId"]
        response = requests.delete(f"{endpoint}/{id}", headers=base_header)
        print(f"Delete: {sub['eventType']} - {id} -> Code: {response.status_code}")


def create_subscriptions(callback_base):
    delete_old_subscriptions()
    endpoint = resourceurl + "/event-subscriptions"
    headers = base_header.copy()
    headers['Content-Type'] = 'application/json'
    events = [
        "voucher.created",
        #"invoice.created",
    ]
    for ev in events:
        url = f"https://{callback_base}/{ev.replace('.', '/')}"
        data = {
            "eventType": ev,
            "callbackUrl": url
        }
        response = requests.post(endpoint, headers=headers, json=data)
        if response.status_code != 201:
            print(f"error creating event {ev}! code {response.status_code}")
        else:
            print(f"lexoffice event {ev} subscribed at {url}")


def pull_voucher(resource_id:str):
    endpoint = resourceurl + f"/vouchers/{resource_id}"
    response = requests.get(endpoint, headers=base_header)
    if response.status_code < 210:
        return response.json()
    else:
        print(f"Error fetching voucher: {response.status_code}")
        return None


def download_file(resource_id:str):
    endpoint = resourceurl + f"/files/{resource_id}"
    response = requests.get(endpoint, headers=base_header)
    if response.status_code < 210:
        cdisp = response.headers["Content-Disposition"]
        cdisp.split("; ")
        filename = cdisp[1].replace("filename=", "")
        datafile = here / "downloads" / filename
        with open(datafile, "wb") as f:
            f.write(response.content)
        return datafile
    else:
        print(f"Error fetching file: {response.status_code}")
        return None
