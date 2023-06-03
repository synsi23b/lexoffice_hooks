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


def _create_contact(parsed):
    name = parsed["supplier_company_registrations"]
    address = parsed["supplier_address"]
    pd = parsed["supplier_payment_details"]
    iban, swift, routing = "", "", ""
    if pd:
        iban = pd["iban"]
        swift = pd["swift"]
        routing = pd["routing_number"]
    return lexoffice.create_company(name, address, iban, swift, routing)


def _noop(inval):
    return inval["value"]


def _localdtiso(inval):
    d = datetime.strptime(inval["value"], "%Y-%m-%d")
    dtz = TZ.localize(d)
    return dtz.isoformat()


def _fill_if_exists(lex, lexkey, mindee, mindeekey, exctractor=_noop):
    if mindee[mindeekey] is not None:
        logging.info(f"Replacing {lexkey}:{lex[lexkey]} with ")
        lex[lexkey] = exctractor(mindee[mindeekey])


def update_lex_voucher(lex, mindee):
    pred = mindee["document"]["inference"]["prediction"]
    _fill_if_exists(lex, "voucherNumber", pred, "invoice_number")
    _fill_if_exists(lex, "voucherDate", pred, "date", _localdtiso)
    _fill_if_exists(lex, "dueDate", pred, "due_date", _localdtiso)
    _fill_if_exists(lex, "totalGrossAmount", pred, "total_amount")
    _fill_if_exists(lex, "totalTaxAmount", pred, "total_tax")
    
    lex["useCollectiveContact"] = False
    contact = lexoffice.pull_contact(lex["contactId"])
    if contact:
        if not lexoffice.compare_contact(contact, mindee["supplier_company_registrations"]):
            lex["contactId"] = _create_contact(mindee)
    else:
        lex["contactId"] = _create_contact(mindee)

    
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
