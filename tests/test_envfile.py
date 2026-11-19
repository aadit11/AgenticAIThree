import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from lib.envfile import load_project_env


class EnvFileTests(unittest.TestCase):
    def test_runtime_file_fills_only_missing_names(self):
        previous_key = os.environ.get("OPENAI_API_KEY")
        previous_runtime = os.environ.get("LUMEN_RUNTIME_ENV")
        os.environ.pop("EMAIL_IMAP_HOST", None)
        with TemporaryDirectory() as directory:
            runtime = Path(directory) / "runtime.env"
            runtime.write_text("EMAIL_IMAP_HOST=imap.gmail.com\nOPENAI_API_KEY=from-file\n", encoding="utf-8")
            os.environ["LUMEN_RUNTIME_ENV"] = str(runtime)
            os.environ["OPENAI_API_KEY"] = "already-set"
            try:
                load_project_env(Path(directory) / "missing.env")
                self.assertEqual(os.environ["EMAIL_IMAP_HOST"], "imap.gmail.com")
                self.assertEqual(os.environ["OPENAI_API_KEY"], "already-set")
            finally:
                os.environ.pop("EMAIL_IMAP_HOST", None)
                if previous_key is None:
                    os.environ.pop("OPENAI_API_KEY", None)
                else:
                    os.environ["OPENAI_API_KEY"] = previous_key
                if previous_runtime is None:
                    os.environ.pop("LUMEN_RUNTIME_ENV", None)
                else:
                    os.environ["LUMEN_RUNTIME_ENV"] = previous_runtime


if __name__ == "__main__":
    unittest.main()
