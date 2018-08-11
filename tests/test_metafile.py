import unittest

from pyrrent.metafile import Metafile

_TEST_PIECES_HASH = b'\x00' * 20 + b'\x01' * 20
_TEST_ENCODED_METAFILE = (
    b'd8:announce23:http://www.test-url.com'
    b'4:infod12:piece lengthi100e'
    b'6:pieces40:\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    b'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
    b'4:name4:base'
    b'5:filesld6:lengthi120e4:pathl4:dir15:file1eed6:lengthi50e4:pathl5:file2eeeee'
)


class MetafileTests(unittest.TestCase):
    def test_parsing(self):
        metafile = Metafile.parse(_TEST_ENCODED_METAFILE)

        self.assertEqual(metafile.announce_url, 'http://www.test-url.com')
        self.assertEqual(len(metafile.pieces), 2)
        self.assertEqual(metafile.pieces[0].hash, b'\x00' * 20)
        self.assertEqual(metafile.pieces[0].length, 100)
        self.assertEqual(metafile.pieces[1].hash, b'\x01' * 20)
        self.assertEqual(metafile.pieces[1].length, 70)
        self.assertEqual(len(metafile.info_hash), 20)
        self.assertEqual(len(metafile.files), 2)
        self.assertEqual(metafile.files[0].length, 120)
        self.assertEqual(metafile.files[0].path, 'base/dir1/file1')
        self.assertEqual(metafile.files[1].length, 50)
        self.assertEqual(metafile.files[1].path, 'base/file2')