import asyncio
import logging
from urllib.parse import urlencode

import aiohttp

from pyrrent import bencoding


class AnnouncerError(Exception):
    pass


class AnnounceResult:
    def __init__(self, complete, incomplete, peers):
        self.complete = complete
        self.incomplete = incomplete
        self.peers = peers


class HTTPAnnouncer:
    def __init__(self, url, download_info, coordinator, timeout=5, loop=None):
        self._url = url
        self._download_info = download_info
        self._coordinator = coordinator
        self._timeout = timeout
        self._loop = loop if loop else asyncio.get_event_loop()
        self._announce_event = asyncio.Event()
        self._next_event = 'normal'
        self._session = aiohttp.ClientSession(loop=self._loop,
                                              read_timeout=timeout,
                                              conn_timeout=timeout)
        self._wake_up_task = None
        self._tracker_id = None

    def stop(self):
        self._set_event('stopped')

    def announce_completion(self):
        self._set_event('completed')

    def _set_event(self, event):
        if self._wake_up_task:
            self._wake_up_task.cancel()
            self._wake_up_task = None

        self._next_event = event
        self._announce_event.set()

    async def announcing(self):
        logging.info(f'Starting announcing to {self._url}')

        try:
            await self._announce('started')
        except AnnouncerError as e:
            logging.error(f'Failed to announce started to {self._url}. Exception: {e}')
            self._coordinator.process_announcer_error('started')

        while True:
            await self._announce_event.wait()
            self._announce_event.clear()
            announce_event = self._next_event
            self._next_event = 'normal'

            try:
                await self._announce(announce_event)
            except AnnouncerError as e:
                logging.warning(f'Failed to announce {announce_event} to {self._url}. Exception: {e}')
                self._coordinator.process_announcer_error(announce_event)

            if announce_event == 'stopped':
                logging.info(f'Stopped announcing to {self._url}')
                return

    async def _announce(self, event='normal'):
        logging.debug(f'Announcing {event} to {self._url}')

        params = self._get_announce_params(event)
        full_url = self._url + '?' + urlencode(params)

        try:
            async with self._session.get(full_url) as resp:
                resp.raise_for_status()
                response_content = await resp.read()
        except asyncio.TimeoutError as e:
            raise AnnouncerError(f'Timeouted while announcing to {self._url}') from e
        except aiohttp.ClientError as e:
            raise AnnouncerError(f'Connection error while announcing to {self._url}') from e

        announce_result, interval, tracker_id = self._parse_tracker_response(response_content)
        if tracker_id:
            self._tracker_id = tracker_id

        self._wake_up_task = self._loop.call_later(interval, self._wake_up)
        logging.info(f'Announce result from {self._url}. Seeders: {announce_result.complete}. '
                     f'Leechers: {announce_result.incomplete}. Peers given: {len(announce_result.peers) % 6}')
        self._coordinator.process_announce_result(announce_result)

    def _get_announce_params(self, event):
        params = {
            'event': event,
            'info_hash': self._download_info.info_hash,
            'peer_id': self._download_info.peer_id,
            'port': self._download_info.port,
            'downloaded': self._download_info.downloaded,
            'uploaded': self._download_info.uploaded,
            'left': self._download_info.left,
            'compact': 1,
            'numwant': 20, # TODO
        }
        if self._tracker_id:
            params['trackerid'] = self._tracker_id

        return params

    def _parse_tracker_response(self, encoded_response):
        try:
            response = bencoding.decode(encoded_response)
        except bencoding.BencodingError as e:
            raise AnnouncerError(f'Invalid response from tracker {self._url}') from e

        if not isinstance(response, dict):
            raise AnnouncerError(f'Invalid response from tracker {self._url}. Bad item type')

        try:
            complete = response['complete']
            incomplete = response['incomplete']
            interval = response['interval']
            peers = response['peers']
        except KeyError as e:
            raise AnnouncerError(f'Invalid response from tracker {self._url}. Missing field {e}')

        if not isinstance(complete, int):
            raise AnnouncerError(f'Invalid response from tracker {self._url}. Field complete not integer')
        if not isinstance(incomplete, int):
            raise AnnouncerError(f'Invalid response from tracker {self._url}. Field incomplete not integer')
        if not isinstance(interval, int):
            raise AnnouncerError(f'Invalid response from tracker {self._url}. Field interval not integer')
        if not isinstance(peers, bytes):
            raise AnnouncerError(f'Invalid response from tracker {self._url}. Field peers not bytes')
        if len(peers) % 6:
            raise AnnouncerError(f'Invalid response from tracker {self._url}. Field peers not multiple of 6 bytes')

        tracker_id = response.get('trackerid')
        if tracker_id and not isinstance(tracker_id, (int, bytes)):
            raise AnnouncerError(f'Invalid response from tracker {self._url}. Field trackerid not bytes or int')

        result = AnnounceResult(complete, incomplete, peers)
        return result, interval, tracker_id

    def _wake_up(self):
        self._announce_event.set()
        self._wake_up_task = None