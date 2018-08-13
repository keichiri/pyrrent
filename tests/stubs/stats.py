class StatsStub:
    def __init__(self, downloaded, uploaded, left):
        self._downloaded = downloaded
        self._uploaded = uploaded
        self._left = left
        self._dl_call_count = 0
        self._ul_call_count = 0
        self._left_call_count = 0

    @property
    def downloaded(self):
        dl = self._downloaded[self._dl_call_count]
        self._dl_call_count += 1
        return dl

    @property
    def uploaded(self):
        ul = self._uploaded[self._ul_call_count]
        self._ul_call_count += 1
        return ul

    @property
    def left(self):
        left = self._left[self._left_call_count]
        self._left_call_count += 1
        return left