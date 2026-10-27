import sys, os, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from poe_inspector import timeless as t


class Core(unittest.TestCase):
    def test_bounded_range(self):
        r = t.TinyMT([18157, 3621])
        self.assertTrue(all(0 <= r.below(37) < 37 for _ in range(1000)))

    def test_deterministic(self):
        self.assertEqual([t.TinyMT([1, 2]).next() for _ in range(3)], [t.TinyMT([1, 2]).next() for _ in range(3)])
        self.assertNotEqual(t.TinyMT([1, 2]).next(), t.TinyMT([1, 3]).next())


if __name__ == "__main__":
    unittest.main()
