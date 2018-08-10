import unittest

from pyrrent.bencoding import encode, decode, BencodingError


class BencodingTests(unittest.TestCase):
    def test_bencode_int(self):
        inputs = [0, -1, 1000, 1000000000]
        expected_outputs = [b'i0e', b'i-1e', b'i1000e', b'i1000000000e']

        for i, input in enumerate(inputs):
            expected_output = expected_outputs[i]
            output = encode(input)
            self.assertEqual(output, expected_output)

    def test_encode_bytes(self):
        inputs = [b'', b'test', b'\x00\x01\x02\x03\x04\x05\xff']
        expected_outputs = [b'0:', b'4:test', b'7:\x00\x01\x02\x03\x04\x05\xff']

        for i, input in enumerate(inputs):
            expected_output = expected_outputs[i]
            output = encode(input)
            self.assertEqual(output, expected_output)

    def test_encode_str(self):
        inputs = ['', 'test']
        expected_outputs = [b'0:', b'4:test']

        for i, input in enumerate(inputs):
            expected_output = expected_outputs[i]
            output = encode(input)
            self.assertEqual(output, expected_output)

        invalid_inputs = ['test\xff', 'fooĎ']

        for invalid_input in invalid_inputs:
            with self.assertRaises(BencodingError):
                encode(invalid_input)

    def test_encode_list(self):
        inputs = [[], [1, 2], [[[]]], [1, 2, 'foo', ['bar'], ['spam', 'eggs']]]
        expected_outputs = [b'le', b'li1ei2ee', b'llleee', b'li1ei2e3:fool3:barel4:spam4:eggsee']

        for i, input in enumerate(inputs):
            expected_output = expected_outputs[i]
            output = encode(input)
            self.assertEqual(output, expected_output)

    def test_encode_dict(self):
        inputs = [
            {},
            {'foo': 'bar'},
            {'foo': {'bar': {'spam': [1, 2, 'eggs']}}}
        ]
        expected_outputs = [b'de', b'd3:foo3:bare', b'd3:food3:bard4:spamli1ei2e4:eggseeee']

        for i, input in enumerate(inputs):
            expected_output = expected_outputs[i]
            output = encode(input)
            self.assertEqual(output, expected_output)

        invalid_inputs = [
            {'foo': 'bar', 'spam\xff': 'eggs'},
            {3: 'foo'},
        ]

        for invalid_input in invalid_inputs:
            with self.assertRaises(BencodingError):
                encode(invalid_input)

    def test_decode_int(self):
        inputs = [b'i0e', b'i-1e', b'i1000e', b'i1000000000e']
        expected_outputs = [0, -1, 1000, 1000000000]

        for i, input in enumerate(inputs):
            expected_output = expected_outputs[i]
            output = decode(input)
            self.assertEqual(output, expected_output)

    def test_decode_bytes(self):
        inputs = [b'0:', b'4:test', b'7:\x00\x01\x02\x03\x04\x05\xff']
        expected_outputs = [b'', b'test', b'\x00\x01\x02\x03\x04\x05\xff']

        for i, input in enumerate(inputs):
            expected_output = expected_outputs[i]
            output = decode(input)
            self.assertEqual(output, expected_output)

    def test_decode_list(self):
        inputs = [b'le', b'li1ei2ee', b'llleee', b'li1ei2e3:fool3:barel4:spam4:eggsee']
        expected_outputs = [[], [1, 2], [[[]]], [1, 2, b'foo', [b'bar'], [b'spam', b'eggs']]]

        for i, input in enumerate(inputs):
            expected_output = expected_outputs[i]
            output = decode(input)
            self.assertEqual(output, expected_output)

    def test_decode_dict(self):
        inputs = [b'de', b'd3:foo3:bare', b'd3:food3:bard4:spamli1ei2e4:eggseeee']
        expected_outputs = [
            {},
            {'foo': b'bar'},
            {'foo': {'bar': {'spam': [1, 2, b'eggs']}}}
        ]

        for i, input in enumerate(inputs):
            expected_output = expected_outputs[i]
            output = decode(input)
            self.assertEqual(output, expected_output)

        invalid_inputs = [
            b'd3:foo3:bar5:spam\xff4:eggse',
            b'di3e3:foo',
        ]

        for invalid_input in invalid_inputs:
            with self.assertRaises(BencodingError):
                decode(invalid_input)
