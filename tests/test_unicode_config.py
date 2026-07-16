import os
import shutil
import sys
import tempfile
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import gangcord


UNICODE_EXAMPLES = (
    "Änderungen für Jürgen Müller",
    "Größe, Oberfläche und Überprüfung",
    "Straße, München, Köln und Düsseldorf",
    "Accents: café, déjà vu; apostrophe: user’s; symbol: ✓",
)


class ConfigPathTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="gangcord-test-")
        self.originals = {
            "USER_DATA_DIR": gangcord.USER_DATA_DIR,
            "LOG_DIR": gangcord.LOG_DIR,
            "CACHE_DIR": gangcord.CACHE_DIR,
            "TEMP_DIR": gangcord.TEMP_DIR,
            "CONFIG_PATH": gangcord.CONFIG_PATH,
            "LEGACY_CONFIG_PATHS": gangcord.LEGACY_CONFIG_PATHS,
        }
        gangcord.USER_DATA_DIR = os.path.join(self.temp_dir, "Gangcord")
        gangcord.LOG_DIR = os.path.join(gangcord.USER_DATA_DIR, "Logs")
        gangcord.CACHE_DIR = os.path.join(gangcord.USER_DATA_DIR, "Cache")
        gangcord.TEMP_DIR = os.path.join(self.temp_dir, "Temp", "Gangcord")
        gangcord.CONFIG_PATH = os.path.join(gangcord.USER_DATA_DIR, "config.json")
        gangcord.LEGACY_CONFIG_PATHS = ()
        gangcord.LAST_CONFIG_ERROR = ""

    def tearDown(self):
        for name, value in self.originals.items():
            setattr(gangcord, name, value)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_unicode_round_trip_uses_utf8(self):
        config = dict(gangcord.DEFAULT_CONFIG)
        config["unicode_test_values"] = list(UNICODE_EXAMPLES)

        self.assertTrue(gangcord.save_config(config), gangcord.LAST_CONFIG_ERROR)
        with open(gangcord.CONFIG_PATH, "r", encoding="utf-8") as handle:
            saved_text = handle.read()
        for example in UNICODE_EXAMPLES:
            self.assertIn(example, saved_text)

        reloaded = gangcord.load_config()
        self.assertEqual(list(UNICODE_EXAMPLES), reloaded["unicode_test_values"])

    def test_damaged_config_falls_back_to_defaults(self):
        os.makedirs(gangcord.USER_DATA_DIR, exist_ok=True)
        with open(gangcord.CONFIG_PATH, "w", encoding="utf-8") as handle:
            handle.write("{ damaged json")

        loaded = gangcord.load_config()
        self.assertEqual(gangcord.DEFAULT_CONFIG["theme_mode"], loaded["theme_mode"])
        self.assertIn("could not be read", gangcord.LAST_CONFIG_ERROR.lower())


if __name__ == "__main__":
    unittest.main()
