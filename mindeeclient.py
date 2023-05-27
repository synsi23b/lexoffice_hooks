from dotenv import load_dotenv
import os
from mindee import Client, documents


load_dotenv()


def parse(path):
    # Init a new client
    mindee_client = Client(api_key=os.getenv("mindee_apikey"))

    # Load a file from disk
    input_doc = mindee_client.doc_from_path(str(path))

    # Parse the Financial Document by passing the appropriate type
    result = input_doc.parse(documents.TypeFinancialDocumentV1)

    # Print a brief summary of the parsed data
    print(result.document)
    return result


