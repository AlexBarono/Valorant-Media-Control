import os
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ProjectIntegrityTests(unittest.TestCase):
    def test_removed_header_images_are_not_present_or_referenced(self):
        removed_names = (
            "Gangcord.gif",
            "Erstaz Bild für das Gif.png",
            "logo der app.png",
        )
        source_path = os.path.join(PROJECT_ROOT, "src", "gangcord.py")
        with open(source_path, "r", encoding="utf-8") as handle:
            source = handle.read()
        self.assertNotIn("PhotoImage", source)
        for name in removed_names:
            self.assertFalse(os.path.exists(os.path.join(PROJECT_ROOT, name)))
            self.assertNotIn(name, source)

    def test_release_version_is_consistent(self):
        expected = 'APP_VERSION = "2.0.1"'
        for relative_path in (("src", "gangcord.py"), ("src", "game_watcher.py")):
            path = os.path.join(PROJECT_ROOT, *relative_path)
            with open(path, "r", encoding="utf-8") as handle:
                self.assertIn(expected, handle.read())

    def test_installer_does_not_wait_for_the_background_watcher(self):
        installer_path = os.path.join(PROJECT_ROOT, "installer", "Gangcord.iss")
        with open(installer_path, "r", encoding="utf-8-sig") as handle:
            installer = handle.read()
        watcher_run = next(
            line
            for line in installer.splitlines()
            if 'Parameters: "{code:GetAutoLaunchParameters}"' in line
        )
        self.assertIn("nowait", watcher_run)
        self.assertNotIn("waituntilterminated", watcher_run)


if __name__ == "__main__":
    unittest.main()
