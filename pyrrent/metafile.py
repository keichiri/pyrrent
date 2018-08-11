import os
import hashlib

from pyrrent.bencoding import (encode, decode, BencodingError)


class MetafileError(Exception):
    pass


class Metafile:
    @classmethod
    def parse(cls, encoded_content):
        try:
            decoded_content = decode(encoded_content)
        except BencodingError as e:
            raise MetafileError(f'Failed to decode provided content') from e

        try:
            announce_url = decoded_content['announce'].decode('ascii')
            info = decoded_content['info']
            if not isinstance(info, dict):
                raise MetafileError(f'Invalid metafile. Invalid info field type: {type(info)}')

            files = FileInfo.from_info(info)
            pieces = Piece.from_info(info)
        except KeyError as e:
            raise MetafileError(f'Missing required metafile field: {e}') from e
        except ValueError as e:
            raise MetafileError(f'Metafile contains invalid field') from e

        if not files:
            raise MetafileError(f'Invalid metafile. Empty files list')

        if not pieces:
            raise MetafileError(f'Invalid metafile. Empty pieces list')

        pieces[-1].length = sum(file.length for file in files) % pieces[-1].length

        # Must use originally encoded, since info hash can encode to different value
        # because it is an unordered map
        encoded_info = encode(info)
        info_index = encoded_content.find(b'4:info') + 6
        original_encoded_info = encoded_content[info_index:info_index + len(encoded_info)]
        info_hash = hashlib.sha1(original_encoded_info).digest()

        return cls(info_hash, announce_url, pieces, files)


    def __init__(self, info_hash, announce_url, pieces, files):
        self.info_hash = info_hash
        self.announce_url = announce_url
        self.pieces = pieces
        self.files = files


class FileInfo:
    @classmethod
    def from_info(cls, info):
        name = info['name'].decode()
        length = info.get('length')
        if length:
            if not isinstance(length, int):
                raise MetafileError(f'Invalid metafile. Invalid file length field type: {type(length)}')

            file_info = cls(name, length)
            return [file_info]

        file_dicts = info['files']
        file_infos = []

        for file_dict in file_dicts:
            length = file_dict['length']
            if not isinstance(length, int):
                raise MetafileError(f'Invalid metafile. Invalid file length field type: {type(length)}')

            path_items = file_dict['path']
            if not isinstance(path_items, list):
                raise MetafileError(f'Invalid metafile. Invalid path field type: {type(path_items)}')

            try:
                path_items = [path_item.decode() for path_item in path_items]
                path = os.path.join(name, *path_items)
            except Exception as e:
                raise MetafileError(f'Invalid path for file: {path_items}') from e

            file_info = cls(path, length)
            file_infos.append(file_info)

        return file_infos

    def __init__(self, path, length):
        self.path = path
        self.length = length


# TODO - maybe verify the length of pieces. It should be in a list of generally allowed lengths
class Piece:
    __slots__ = 'index', 'hash', 'length'

    @classmethod
    def from_info(cls, info):
        length = info['piece length']
        hashes = info['pieces']
        if len(hashes) % 20:
            raise MetafileError(f'Pieces hash not exact multiple of 20 bytes: {len(hashes)}')

        piece_count = len(hashes) // 20
        pieces = []

        for i in range(piece_count):
            index = i * 20
            piece_hash = hashes[index:index+20]
            piece = cls(i, piece_hash, length)
            pieces.append(piece)

        return pieces


    def __init__(self, index, hash, length):
        self.index = index
        self.hash = hash
        self.length = length

