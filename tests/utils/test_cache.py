import unittest

from pyrrent.utils.cache import Cache


class CacheTests(unittest.TestCase):
    def test_put_get(self):
        cache = Cache(5)
        self.assertIsNone(cache.get('key'))

        cache.put('key', 'value')
        self.assertEqual(cache.get('key'), 'value')

    def test_purge(self):
        cache = Cache(10)

        for i in range(10):
            cache.put(i, i * i)

        self.assertEqual(len(cache._records), 10)

        cache.get(2)

        cache.put(10, 100)

        self.assertEqual(len(cache._records), 8)

        self.assertIsNone(cache.get(0))
        self.assertIsNone(cache.get(1))
        self.assertEqual(cache.get(2), 4)
        self.assertIsNone(cache.get(3))
        self.assertEqual(cache.get(4), 16)
        self.assertEqual(cache.get(5), 25)
        self.assertEqual(cache.get(6), 36)
        self.assertEqual(cache.get(7), 49)
        self.assertEqual(cache.get(8), 64)
        self.assertEqual(cache.get(9), 81)
        self.assertEqual(cache.get(10), 100)
