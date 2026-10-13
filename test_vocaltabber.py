import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
import vocaltabber as v


class ValidationTests(unittest.TestCase):
    def rejected(self, args):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as cm:
            v.main(args)
        self.assertEqual(cm.exception.code, 2)

    def test_missing_input(self):
        self.rejected(['/does/not/exist.mp3'])

    def test_empty_and_wrong_extension(self):
        with tempfile.TemporaryDirectory() as d:
            file = Path(d) / 'empty.mp3'
            file.touch()
            self.rejected([str(file)])
            other = Path(d) / 'text.txt'
            other.write_text('hello')
            self.rejected([str(other)])

    def test_bad_timeout(self):
        with tempfile.TemporaryDirectory() as d:
            file = Path(d) / 'input.mp3'
            file.write_bytes(b'not audio')
            self.rejected([str(file), '--timeout', '0'])

    def test_stage_failure(self):
        with self.assertRaises(v.PipelineError):
            v.run_command([sys.executable, '-c', 'raise SystemExit(7)'], 5)

    def test_stage_timeout(self):
        with self.assertRaises(v.PipelineError):
            v.run_command([sys.executable, '-c', 'import time; time.sleep(10)'], 0.1)


if __name__ == '__main__':
    unittest.main()
