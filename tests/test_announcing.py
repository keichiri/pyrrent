import asyncio
import unittest

from pyrrent.announcing import HTTPAnnouncer
from pyrrent.bencoding import decode

from tests.stubs.http_tracker import HTTPTrackerStub
from tests.stubs.download_info import DownloadInfoStub
from tests.stubs.coordinator import PeerCoordinatorStub


_HTTP_TRACKER_STUB_PORT = 30701


def _tracker_response(seeders, leechers, interval=1, peers=b'', tracker_id=''):
    resp = {
        'complete': seeders,
        'incomplete': leechers,
        'interval': interval,
        'peers': peers,
    }
    if tracker_id:
        resp['trackerid'] = tracker_id
    return resp


class HTTPAnnouncerTests(unittest.TestCase):
    def test_started(self):
        loop = asyncio.get_event_loop()
        download_info = DownloadInfoStub('peer_id', b'info_hash', 5000, [0], [0], [10000])
        coordinator = PeerCoordinatorStub()
        response = _tracker_response(10, 20, peers=b'\x01\x02\x03\x04\x05\x06')
        http_tracker = HTTPTrackerStub('0.0.0.0', _HTTP_TRACKER_STUB_PORT, [response])
        announcer = HTTPAnnouncer(f'http://127.0.0.1:{_HTTP_TRACKER_STUB_PORT}',
                                  download_info,
                                  coordinator)

        loop.run_until_complete(http_tracker.start())
        loop.run_until_complete(asyncio.sleep(0.01))

        loop.create_task(announcer.announcing())

        loop.run_until_complete(asyncio.sleep(0.01))
        http_tracker.stop()

        self.assertEqual(len(http_tracker.requests), 1)
        announce_0 = http_tracker.requests[0]
        self.assertEqual(announce_0['info_hash'], 'info_hash')
        self.assertEqual(announce_0['peer_id'], 'peer_id')
        self.assertEqual(announce_0['port'], '5000')
        self.assertEqual(announce_0['downloaded'], '0')
        self.assertEqual(announce_0['uploaded'], '0')
        self.assertEqual(announce_0['left'], '10000')
        self.assertEqual(announce_0['event'], 'started')

        self.assertEqual(len(coordinator.announce_results), 1)
        result_0 = coordinator.announce_results[0]
        self.assertEqual(result_0.complete, 10)
        self.assertEqual(result_0.incomplete, 20)
        self.assertEqual(result_0.peers, b'\x01\x02\x03\x04\x05\x06')