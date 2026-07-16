import os
import sys
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import game_watcher


class GameWatcherTests(unittest.TestCase):
    def test_process_selection_modes(self):
        valorant = {"valorant-win64-shipping.exe"}
        league = {"leagueclientux.exe"}
        both = valorant | league

        self.assertFalse(game_watcher.should_launch("none", both))
        self.assertTrue(game_watcher.should_launch("valorant", valorant))
        self.assertFalse(game_watcher.should_launch("valorant", league))
        self.assertTrue(game_watcher.should_launch("lol", league))
        self.assertFalse(game_watcher.should_launch("lol", valorant))
        self.assertTrue(game_watcher.should_launch("both", valorant))
        self.assertTrue(game_watcher.should_launch("both", league))

    def test_process_scan_returns_normalized_names(self):
        names = game_watcher.running_process_names()
        self.assertIsInstance(names, set)
        self.assertTrue(names)
        self.assertTrue(all(name == name.lower() for name in names))


if __name__ == "__main__":
    unittest.main()
