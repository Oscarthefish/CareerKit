import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.storage.file_storage import get_application_folder


class ApplicationFolderTests(unittest.TestCase):
    def test_folder_names_are_safe_and_unique(self):
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            with patch("app.storage.file_storage.DATA_DIR", data_dir):
                first = get_application_folder("Acme / NZ", "SOC Analyst")
                second = get_application_folder("Acme / NZ", "SOC Analyst")

            self.assertTrue(first.is_dir())
            self.assertTrue((first / "exports").is_dir())
            self.assertNotEqual(first, second)
            self.assertNotIn("/", first.name)
            self.assertTrue(second.name.endswith("_2"))


if __name__ == "__main__":
    unittest.main()
