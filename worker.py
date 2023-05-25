import queue
from threading import Thread

class Worker:
    def __init__(self):
        self._q = queue.Queue()
        self._working = True
        self._t = Thread(target=self.runner)
        self._t.start()

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
                elem = self._q.get(timeout=5.0)
                print(f"Working on: {elem}")
            except queue.Empty:
                pass
        print("Worker runner finished")
    