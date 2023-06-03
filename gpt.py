from dotenv import load_dotenv
import os
import openai
import re
import logging


load_dotenv()
openai.api_key = os.getenv("openai_key")


def find_best_spending_category(line_item, spending_categories, default):
    spending_names = '\n'.join([p["name"] for p in spending_categories])

    proompt = f"\
Out of the following list, \
which term would best describe the item \"{line_item}\". \
In your answer, put the selected item inside curly brackets.\n\
The list:\n\
{spending_names}"
    
    logging.info(proompt)
    response = openai.Completion.create(
         model="text-davinci-003",
         prompt=proompt,
         temperature=0, max_tokens=50)
    logging.info(response)

    res = default
    pattern = re.compile(r"\{(.+?)\}")
    for ch in response["choices"]:
        mc = pattern.findall(ch["text"])
        if mc:
            text = mc[0]
            for p in spending_categories:
                if p["name"].startswith(text):
                    res = p
                    break
    return res

if __name__ == "__main__":
    import lexoffice
    line_item = "Robot Programming for Merck Experiments – PhD-Project @ leap in time Lab"
    logging.info(find_best_spending_category(line_item, lexoffice.get_postings_outgo(), lexoffice.BASE_SPENDING))