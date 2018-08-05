import time


class Cache:
    def __init__(self, max_records):
        self._max_record_count = max_records
        self._records = {}

    def put(self, key, data):
        if key in self._records:
            return

        if len(self._records) == self._max_record_count:
            self._purge()

        ts = time.time()
        new_record = _CacheRecord(key, ts, data)
        self._records[key] = new_record

    def get(self, key):
        record = self._records.get(key)
        if not record:
            return None

        record.timestamp = time.time()
        return record.data

    def _purge(self):
        to_remove = self._max_record_count * 1 // 3
        all_records = list(self._records.values())
        all_records.sort(key=lambda record: record.timestamp)

        for record in all_records[:to_remove]:
            self._records.pop(record.key)


class _CacheRecord:
    __slots__ = 'key', 'timestamp', 'data'


    def __init__(self, key, timestamp, data):
        self.key = key
        self.timestamp = timestamp
        self.data = data