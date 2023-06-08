from dotenv import load_dotenv
import os
#from mindee import Client, documents
import requests
from datetime import datetime
import pytz
import lexoffice
from gpt import find_best_spending_category
import logging


load_dotenv()
TZ = pytz.timezone("Europe/Berlin")


def parse(path):
    # # Init a new client
    # mindee_client = Client(api_key=os.getenv("mindee_apikey"))

    # # Load a file from disk
    # input_doc = mindee_client.doc_from_path(str(path))

    # # Parse the Financial Document by passing the appropriate type
    # result = input_doc.parse(documents.TypeFinancialDocumentV1)

    # # Print a brief summary of the parsed data
    # print(result.document)
    # return result
    api_key = os.getenv("mindee_apikey")
    account = "mindee"
    endpoint = "financial_document"
    version = "1.1"

    url = f"https://api.mindee.net/v1/products/{account}/{endpoint}/v{version}/predict"

    with open(path, "rb") as file_handle:
        files = {"document": file_handle}
        headers = {"Authorization": f"Token {api_key}"}
        response = requests.post(url, files=files, headers=headers)

    json_response = response.json()

    if not response.ok:
        raise RuntimeError(json_response["api_request"]["error"])

    return json_response


def _get_supplier_name(parsed:dict):
    name = parsed.get("supplier_name", {"value": "Unknown"})
    regi = parsed.get("supplier_company_registrations", [])
    if regi:
        return regi[0]
    return name["value"]


def _minget(parsed, key, default):
    v = parsed.get(key, {})
    if type(v) == dict:
        return v.get("value", default)
    return v


def _create_contact(parsed):
    name = _get_supplier_name(parsed)
    address = _minget(parsed, "supplier_address", "")
    pd = _minget(parsed, "supplier_payment_details", None)
    iban, swift, routing = "", "", ""
    if pd:
        iban = pd[0]["iban"]
        swift = pd[0]["swift"]
        routing = pd[0]["routing_number"]
    return lexoffice.create_company(name, address, iban, swift, routing)


def _noop(inval):
    return inval.get("value", None)


def _localdtiso(inval):
    s = inval.get("value", None)
    if s:
        d = datetime.strptime(s, "%Y-%m-%d")
        dtz = TZ.localize(d)
        return dtz.isoformat()
    return None


def _fill_if_exists(lex, lexkey, mindee, mindeekey, exctractor=_noop):
    if mindee.get(mindeekey, None) is not None:
        logging.info(f"Replacing {lexkey}:{lex[lexkey]} with ")
        exvalue = exctractor(mindee[mindeekey])
        if exvalue:
            lex[lexkey] = exvalue 


def update_lex_voucher(lex, mindee):
    pred = mindee["document"]["inference"]["prediction"]
    _fill_if_exists(lex, "voucherNumber", pred, "invoice_number")
    _fill_if_exists(lex, "voucherDate", pred, "date", _localdtiso)
    _fill_if_exists(lex, "dueDate", pred, "due_date", _localdtiso)
    _fill_if_exists(lex, "totalGrossAmount", pred, "total_amount")
    #_fill_if_exists(lex, "totalTaxAmount", pred, "total_tax")
    
    lex["useCollectiveContact"] = False
    contact = lexoffice.pull_contact(lex.get("contactId", None))
    if contact:
        if not lexoffice.compare_contact(contact, _get_supplier_name(pred)):
            lex["contactId"] = _create_contact(pred)
    else:
        lex["contactId"] = _create_contact(pred)

    spending_categories = lexoffice.get_postings_outgo()
    
    vil = []
    for li in pred["line_items"]:
        amount = li["total_amount"]
        tax = li["tax_amount"]
        taxrate = li["tax_rate"]
        if tax is None:
            tax = 0.0
            taxrate = 0.0

        cat = find_best_spending_category(li["description"], spending_categories, 
                                          lexoffice.BASE_SPENDING)

        vil.append({
            "amount": amount,
            "taxAmount": tax,
            "taxRatePercent": taxrate,
            "categoryId": cat["id"]
        })
    lex["voucherItems"] = vil
    lex["totalTaxAmount"] = sum([v["taxAmount"] for v in vil])
