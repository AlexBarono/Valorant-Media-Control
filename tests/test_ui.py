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


class GangcordUiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="gangcord-ui-")
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

    def tearDown(self):
        for name, value in self.originals.items():
            setattr(gangcord, name, value)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_app(self, width, height, scaling=1.0):
        app = gangcord.GangcordApp()
        app.tk.call("tk", "scaling", scaling)
        app.geometry(f"{width}x{height}+0+0")
        app.update_idletasks()
        return app

    def test_supported_window_sizes_build_without_clipping_content(self):
        for width, height in ((1280, 720), (1366, 768), (1920, 1080), (2560, 1440), (3840, 2160)):
            with self.subTest(size=(width, height)):
                app = self.create_app(width, height)
                try:
                    self.assertEqual(3, len(app.scroll_pages))
                    self.assertEqual(3, len(app.notebook.tabs()))
                    for page in app.scroll_pages:
                        self.assertIsNotNone(page["canvas"].bbox("all"))
                finally:
                    app.destroy()

    def test_high_scaling_and_readme_scroll(self):
        for scaling in (1.5, 2.0):
            with self.subTest(scaling=scaling):
                app = self.create_app(1280, 720, scaling)
                try:
                    readme_canvas = app.scroll_pages[2]["canvas"]
                    readme_canvas.yview_moveto(1.0)
                    app.update_idletasks()
                    first, last = readme_canvas.yview()
                    self.assertGreater(first, 0.0)
                    self.assertLessEqual(last, 1.0)
                    hero_texts = [
                        app.hero_canvas.itemcget(item, "text")
                        for item in app.hero_canvas.find_all()
                        if app.hero_canvas.type(item) == "text"
                    ]
                    self.assertIn("Gangcord", hero_texts)
                finally:
                    app.destroy()


if __name__ == "__main__":
    unittest.main()
