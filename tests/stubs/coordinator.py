class PeerCoordinatorStub:
    def __init__(self):
        self._announce_results = []

    @property
    def announce_results(self):
        return self._announce_results

    def process_announce_result(self, result):
        self._announce_results.append(result)
