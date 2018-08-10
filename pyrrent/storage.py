import asyncio
import logging
import os
import stat
from concurrent.futures import ThreadPoolExecutor

from pyrrent.utils import Cache


class StorageError(Exception):
    pass


class Storage:
    @classmethod
    def prepare(cls, base_path):
        if not os.path.exists(base_path):
            logging.info(f'Creating storage at path: {base_path}')

            try:
                os.makedirs(base_path)
            except OSError as e:
                raise StorageError(f'Failed to create storage at: {base_path}') from e
        else:
            logging.info(f'Checking permissions for path: {base_path}')
            _check_ownership_and_permissions(base_path)

        return cls(base_path)

    def __init__(self, base_path):
        self._base_path = base_path
        self._handlers = {}

    def create_handler_for_download(self, download_name, workers=3, cache_size=100, loop=None):
        logging.info(f'Creating handler for download {download_name}')
        if download_name in self._handlers:
            raise StorageError(f'Download {download_name} already active')

        download_path = os.path.join(self._base_path, download_name)
        handler = StorageHandler.create(download_path, workers, cache_size, loop)
        self._handlers[download_name] = handler

        return handler

    def remove_handler_for_download(self, download_name):
        logging.info(f'Removing handler for download {download_name}')
        self._handlers.pop(download_name, None)


class StorageHandler:
    @classmethod
    def create(cls, path, workers, cache_size, loop):
        pieces_path = os.path.join(path, '.pieces')
        if not os.path.exists(pieces_path):
            try:
                os.makedirs(pieces_path, 0o700)
            except OSError as e:
                raise StorageError(f'Failed to create pieces directory') from e

        else:
            _check_ownership_and_permissions(pieces_path)

        return cls(path, pieces_path, workers, cache_size, loop)


    def __init__(self, path, pieces_path, workers, cache_size, loop):
        self._path = path
        self._pieces_path = pieces_path
        self._loop = loop or asyncio.get_event_loop()
        self._pool = ThreadPoolExecutor(max_workers=workers)
        self._cache = Cache(cache_size)

    async def store(self, piece_index, piece_data):
        await self._loop.run_in_executor(self._pool, self._store, piece_index, piece_data)

    async def retrieve(self, piece_index):
        data = self._cache.get(piece_index)
        if data:
            return data

        data = await self._loop.run_in_executor(self._pool, self._retrieve, piece_index)
        self._cache.put(piece_index, data)

        return data

    # NOTE - assumes all the pieces are download, does not perform checks. For example it could
    # list all pieces, multiply by full piece length and check if enough to fill all files
    async def compose_files(self, file_infos):
        await self._loop.run_in_executor(self._pool, self._compose_files, file_infos)

    def _store(self, piece_index, piece_data):
        piece_path = self._get_piece_path(piece_index)
        logging.debug(f'Storing piece with index {piece_index} at path {piece_path}')

        try:
            with open(piece_path, 'wb') as f:
                f.write(piece_data)
        except OSError as e:
            raise StorageError(f'Failed to store piece at: {piece_path}') from e

    def _retrieve(self, piece_index):
        piece_path = self._get_piece_path(piece_index)
        logging.debug(f'Retrieving piece with index {piece_index} from path {piece_path}')

        try:
            with open(piece_path, 'rb') as f:
                content = f.read()
        except OSError as e:
            raise StorageError(f'Failed to retrieve piece from: {piece_path}') from e

        return content

    # TODO - add cleanup and retries here. Long operation so it is good to be resilient as possible
    # TODO - check if last piece is completely used, meaning total file size and total piece size are equal
    def _compose_files(self, file_infos):
        logging.info(f'Composing files at path: {self._path}')
        piece_file_names = self._list_piece_file_names()
        piece_index = 0
        piece_offset = 0

        try:
            for file in file_infos:
                file_path = os.path.join(self._path, file.path)
                file_dir = os.path.dirname(file_path)
                if not os.path.exists(file_dir):
                    os.makedirs(file_dir, 0o700)

                with open(file_path, 'wb') as f:
                    to_write = file.size

                    while to_write:
                        piece_file_name = piece_file_names[piece_index]
                        piece_path = os.path.join(self._pieces_path, piece_file_name)

                        with open(piece_path, 'rb') as pf:
                            pf.seek(piece_offset)
                            content = pf.read(to_write)

                        f.write(content)
                        to_write -= len(content)
                        if to_write:
                            piece_index += 1
                            piece_offset = 0
                        else:
                            piece_offset += len(content)
        except OSError as e:
            raise StorageError(f'Error occurred while composing files') from e

    def _get_piece_path(self, piece_index):
        return os.path.join(self._pieces_path, f'{piece_index}.piece')

    def _list_piece_file_names(self):
        try:
            piece_names = os.listdir(self._pieces_path)
        except OSError as e:
            raise StorageError(f'Failed to list piece files') from e

        piece_names.sort(key=lambda name: int(name.split('.')[0]))
        return piece_names


def _check_ownership_and_permissions(path):
    uid = os.getuid()

    try:
        file_stat = os.stat(path)
    except OSError as e:
        raise StorageError(f'Failed to check stat of path: {path}') from e

    if file_stat.st_uid != uid:
        raise StorageError(f'Current user not owner of path: {path}')

    rw_flag = stat.S_IRUSR | stat.S_IWUSR
    if file_stat.st_mode & rw_flag != rw_flag:
        raise StorageError(f'Current user has no read-write permissions for path: {path}')
