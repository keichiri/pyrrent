from tests.stubs.stats import StatsStub


class DownloadInfoStub:
    def __init__(self, peer_id, info_hash, port, downloaded, uploaded, left):
        self.peer_id = peer_id
        self.info_hash = info_hash
        self.port = port
        self.stats = StatsStub(downloaded, uploaded, left)

    @property
    def downloaded(self):
        return self.stats.downloaded

    @property
    def uploaded(self):
        return self.stats.uploaded

    @property
    def left(self):
        return self.stats.left