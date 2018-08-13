import asyncio

from urllib.parse import parse_qs

from pyrrent.bencoding import encode


class HTTPTrackerStub:
    def __init__(self, address, port, responses, loop=None):
        self._address = address
        self._port = port
        self._responses = responses
        self._loop = loop if loop else asyncio.get_event_loop()
        self._requests = []
        self._exceptions = []
        self._server = None

    def stop(self):
        if self._server:
            self._server.close()

    @property
    def requests(self):
        return self._requests

    async def start(self):
        try:
            self._server = await asyncio.start_server(self._handle_client,
                                                      host=self._address,
                                                      port=self._port,
                                                      loop = self._loop)
        except Exception as e:
            self._exceptions.append(e)

    async def _handle_client(self, reader, writer):
        try:
            data = await reader.read(10240)
            if not data:
                return

            first_line = data.split(b'\r\n')[0]
            path = first_line.split(b' ')[1]
            urlquery = path[path.find(b'?')+1:]
            query_params = {k.decode(): v[0].decode() for k, v in parse_qs(urlquery).items()}

            response_content = self._responses[len(self._requests)]
            full_response = self._prepare_response(response_content)
            self._requests.append(query_params)
            writer.write(full_response)
            await writer.drain()
            writer.close()
        except Exception as e:
            self._exceptions.append(e)
        finally:
            writer.close()

    def _prepare_response(self, content):
        return 'HTTP/1.1 200 OK\r\n\r\n'.encode() + encode(content)
