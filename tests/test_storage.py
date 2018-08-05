import asyncio
import unittest
import os
import shutil

from pyrrent.storage import Storage, StorageError


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
        piece_path = os.path.join(self.TEST_PATH, 'test_download/.pieces/1000.piece')
        with open(piece_path, 'wb') as f:
            f.write(piece_content)

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

