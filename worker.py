import queue
from threading import Thread
from lexoffice import pull_voucher, download_file


def voucher_created(event:dict):
    res_id = event.get("resourceId", "")
    voucher = pull_voucher(res_id)
    if voucher:
        files = voucher.get("files",[])
        if files:
            dl = download_file(files[0])
        else:
            print("Voucher had no files attached")


class Worker:
    def __init__(self):
        self._q = queue.Queue()
        self._working = True
        self._t = Thread(target=self.runner)
        self._t.start()
        self._events = {
            "voucher.created" : voucher_created,
        }

    def put(self, elem):
        print(f"Adding elem to work queue: {elem}")
        self._q.put(elem)

    def stop(self):
        self._working = False
        self._t.join(timeout=20.0)

    def runner(self):
        print("Worker runner start")
        while self._working:
            try:
                func = None
                elem = self._q.get(timeout=5.0)
                print(f"Working on: {elem}")
                if type(elem) == dict:
                    et = elem.get('eventType', None)
                    func = self._events.get(et, None)
                if func:
                    print(f"Running functor {func.__name__}")
                    func(elem)
            except queue.Empty:
                pass
        print("Worker runner finished")
    

if __name__ == "__main__":
    # test voucher cb api
    pass