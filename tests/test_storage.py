import asyncio
import unittest
import os
import shutil

from pyrrent.storage import Storage, StorageError
from pyrrent.metafile import FileInfo


class StorageTests(unittest.TestCase):
    TEST_PATH = '/tmp/pyrrent/tests/storage'


    def setUp(self):
        if not os.path.exists(self.TEST_PATH):
            os.makedirs(self.TEST_PATH)
        else:
            shutil.rmtree(self.TEST_PATH)
        self.storage = Storage.prepare(self.TEST_PATH)
        self.storage_handler = self.storage.create_handler_for_download('test_download')
        self.loop = asyncio.get_event_loop()

    def createTestPiece(self, index, data):
        piece_path = os.path.join(self.TEST_PATH, f'test_download/.pieces/{index}.piece')
        with open(piece_path, 'wb') as f:
            f.write(data)

    def test_storage_raises_error_on_prepare_if_no_permissions(self):
        path = '/bin/storage'

        with self.assertRaises(StorageError):
            Storage.prepare(path)

    def test_create_handler_works_fine_if_pieces_already_exist(self):
        path = '/tmp/pyrrent/tests/storage/test_download_2/.pieces'
        os.makedirs(path)
        piece_content = b'test_piece_data'
        with open(os.path.join(path, '1.piece'), 'wb') as f:
            f.write(piece_content)

        self.storage.create_handler_for_download('test_download_2')

        with open(os.path.join(path, '1.piece'), 'rb') as f:
            current_piece_content = f.read()

        self.assertEqual(piece_content, current_piece_content)

    def test_store_piece(self):
        piece_index = 1000
        piece_data = b'test_piece_data'

        self.loop.run_until_complete(self.storage_handler.store(piece_index, piece_data))

        expected_piece_path = os.path.join(self.TEST_PATH, 'test_download/.pieces/1000.piece')
        with open(expected_piece_path, 'rb') as f:
            content = f.read()

        self.assertEqual(content, piece_data)

    def test_retrieve_piece(self):
        piece_index = 1000
        piece_content = b'test_piece_data'
        self.createTestPiece(piece_index, piece_content)

        retrieved_piece_content = self.loop.run_until_complete(self.storage_handler.retrieve(piece_index))

        self.assertEqual(retrieved_piece_content, piece_content)

    def test_retrieve_piece_returns_cached(self):
        # Checks if piece is retrieved from cache by deleting it from file system between 2 reads
        piece_index = 1000
        piece_content = b'test_piece_data'
        piece_path = os.path.join(self.TEST_PATH, 'test_download/.pieces/1000.piece')
        with open(piece_path, 'wb') as f:
            f.write(piece_content)

        retrieved_piece_content = self.loop.run_until_complete(self.storage_handler.retrieve(piece_index))
        self.assertEqual(retrieved_piece_content, piece_content)

        os.remove(piece_path)

        retrieved_piece_content = self.loop.run_until_complete(self.storage_handler.retrieve(piece_index))
        self.assertEqual(retrieved_piece_content, piece_content)

    def test_compose_files(self):
        file_infos = [
            FileInfo(path='dir1/file1', size=13),
            FileInfo(path='dir1/file2', size=5),
            FileInfo(path='dir1/file3', size=6),
            FileInfo(path='file4', size=20),
            FileInfo(path='dir2/file5', size=6),
            FileInfo(path='dir2/file6', size=3),
        ]
        self.createTestPiece(0, b'\x00' * 10)
        self.createTestPiece(1, b'\x01' * 10)
        self.createTestPiece(2, b'\x02' * 10)
        self.createTestPiece(3, b'\x03' * 10)
        self.createTestPiece(4, b'\x04' * 10)
        self.createTestPiece(5, b'\x05' * 3)

        self.loop.run_until_complete(self.storage_handler.compose_files(file_infos))

        with open(os.path.join(self.storage_handler._path, 'dir1/file1'), 'rb') as f:
            self.assertEqual(f.read(), b'\x00' * 10 + b'\x01' * 3)
        with open(os.path.join(self.storage_handler._path, 'dir1/file2'), 'rb') as f:
            self.assertEqual(f.read(), b'\x01' * 5)
        with open(os.path.join(self.storage_handler._path, 'dir1/file3'), 'rb') as f:
            self.assertEqual(f.read(), b'\x01' * 2 + b'\x02' * 4)
        with open(os.path.join(self.storage_handler._path, 'file4'), 'rb') as f:
            self.assertEqual(f.read(), b'\x02' * 6 + b'\x03' * 10 + b'\x04' * 4)
        with open(os.path.join(self.storage_handler._path, 'dir2/file5'), 'rb') as f:
            self.assertEqual(f.read(), b'\x04' * 6)
        with open(os.path.join(self.storage_handler._path, 'dir2/file6'), 'rb') as f:
            self.assertEqual(f.read(), b'\x05' * 3)
