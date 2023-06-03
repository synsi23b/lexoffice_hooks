import queue
from threading import Thread
from lexoffice import pull_voucher, update_voucher, download_file
import mindeeclient
from util import store_json
import logging


def voucher_created(event:dict):
    res_id = event.get("resourceId", "")
    voucher = pull_voucher(res_id)
    if voucher:
        files = voucher.get("files",[])
        store_json("voucher", res_id, voucher)
        if files:
            dl = download_file(files[0])
            parsed = mindeeclient.parse(dl)
            store_json("mindee", res_id, parsed)
            #dl.unlink()
            # update voucher with data retrieved from mindee
            logging.info("### update voucher with data retrieved from mindee ###")
            mindeeclient.update_lex_voucher(voucher, parsed)
            update_voucher(voucher)
        else:
            logging.info("Voucher had no files attached")


class Worker:
    def __init__(self):
        self._q = queue.Queue()
        self._working = True
        self._events = {
            "voucher.created" : voucher_created,
        }
        self._t = Thread(target=self.runner)
        self._t.start()

    def put(self, elem):
        logging.info(f"Adding elem to work queue: {elem}")
        self._q.put(elem)

    def stop(self):
        self._working = False
        self._t.join(timeout=20.0)

    def runner(self):
        logging.info("Worker runner start")
        while self._working:
            try:
                func = None
                elem = self._q.get(timeout=5.0)
                logging.info(f"Working on: {elem}")
                if type(elem) == dict:
                    et = elem.get('eventType', None)
                    func = self._events.get(et, None)
                if func:
                    logging.info(f"Running functor {func.__name__}")
                    func(elem)
            except queue.Empty:
                pass
            except Exception as e:
                logging.exception(f"Unhandled exption in worker: {type(e)} -> {e}")
        logging.info("Worker runner finished")
    

if __name__ == "__main__":
    # test voucher cb api
    import json
    s = "{'organizationId': '383b8c13-e9e9-43b1-8830-37ce8c3f3436', 'eventType': 'voucher.created', 'resourceId': '21446eb7-f6f7-45cc-9818-c3d8065bde12', 'eventDate': '2023-05-27T03:55:43.368+02:00'}"
    s = s.replace("'", "\"")
    d = json.loads(s)
    voucher_created(d)