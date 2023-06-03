import requests
from dotenv import load_dotenv
import os
from pathlib import Path
import base64
from difflib import SequenceMatcher
import logging


load_dotenv()
here = Path(__file__).parent.resolve()


resourceurl = "https://api.lexoffice.io/v1/"
base_header = {
        'Authorization': f"Bearer {os.getenv('lexoffice_apkikey')}",
        'Accept': 'application/json',
    }


def _base_get(resource:str, expected_status:int=0, added_headers:list=[]):
    endpoint = resourceurl + resource
    headers = base_header.copy()
    headers.update(added_headers)
    response = requests.get(endpoint, headers=headers)
    res = {}
    if expected_status != 0:
        if response.status_code == expected_status:
            res = response.json()
    elif response.status_code >= 200 and response.status_code <= 210:
        res = response.json()
    if type(res) == list:
        return res
    return res.get("content", [])


def _base_post(resource:str, data:dict, expected_status:int=0, added_headers:list=[]):
    endpoint = resourceurl + resource
    headers = base_header.copy()
    added_headers += [('Content-Type', 'application/json')]
    headers.update(added_headers)
    response = requests.post(endpoint, headers=headers, json=data)
    if expected_status != 0:
        if response.status_code == expected_status:
            return response.json()
    elif response.status_code >= 200 and response.status_code <= 210:
        return response.json()
    logging.error(f"Maybe bad POST. Status code {response.status_code}")
    return None


def get_postings_outgo():
    return [p for p in _base_get("posting-categories") if p["type"] == "outgo"]


BASE_SPENDING = None
for post in get_postings_outgo():
    if post["name"] == "Material/Waren":
        BASE_SPENDING = post
        break


def delete_old_subscriptions():
    resource = "event-subscriptions"
    for sub in _base_get(resource):
        id = sub["subscriptionId"]
        response = requests.delete(f"{resourceurl}{resource}/{id}", headers=base_header)
        logging.info(f"Delete: {sub['eventType']} - {id} -> Code: {response.status_code}")


def create_subscriptions(callback_base):
    delete_old_subscriptions()
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
        if _base_post("event-subscriptions", data, 201):
            logging.info(f"lexoffice event {ev} subscribed at {url}")


def pull_voucher(resource_id:str):
    return _base_get(f"vouchers/{resource_id}")


def update_voucher(voucher):
    return _base_post(f"vouchers/{voucher['id']}", voucher)


def download_file(resource_id:str):
    endpoint = resourceurl + f"files/{resource_id}"
    response = requests.get(endpoint, headers=base_header)
    if response.status_code < 210:
        cdisp = response.headers["Content-Disposition"]
        cdisp = cdisp.split(";")
        filename = cdisp[1].replace(" filename=", "")
        datafile = here / "downloads" / filename
        with open(datafile, "wb") as f:
            f.write(base64.b64decode(response.content))
        return datafile
    else:
        logging.error(f"Error fetching file: {response.status_code}")
        return None
    

def pull_contact(resource_id):
    return _base_get(f"contacts/{resource_id}")
    

def _find_contact(name):
    return _base_get(f"contacts/?name={name}")


def find_contact(name, iter=0):
    if iter < 5:
        x = len(name) / 5
        x = round(x * (5 - iter))
        res = _find_contact(name[:min(x + 1, 3)])
        for cont in res:
            if compare_contact(cont, name):
                return cont
        return find_contact(name, iter + 1)
    else:
        return None
    

def compare_contact(contact, name):
    # get company name, not existing for "persons"
    cname = contact.get("name", "")
    ratio = 0.0
    if cname:
        ratio = SequenceMatcher(None, cname, name)
    return ratio > 0.75


def create_company(name, address, iban="", swift="", routing_number=""):
    data = {
        "version": 0,
        "roles": {
            "vendor": {}
        },
        "company": {
            "name": name
        },
        "addresses": {
            "billing": [
                {
                    "street": address,
                    "countryCode": "DE"
                }
            ]
        },
        "note": f"Iban  {iban}\nSwift {swift}\nVerwZweck {routing_number}"
    }
    res = _base_post("contacts", data)
    if res:
        return res.get("content", [{"id": None}])[0]["id"]
    return None


if __name__ == "__main__":
    pass
    #download_file("cc61071e-eb8b-4459-93b3-781748264ce6")
    #print(find_contact("testfirma"))
    #create_company("testfirma", "Weststrasse 59")
    out = get_postings_outgo()
    with open("ausgaben.txt", "w") as f:
        for p in out:
            f.write(p["name"] + "\n")