from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install_pi.sh"


class InstallerTests(unittest.TestCase):
    def test_dry_run_covers_complete_install_without_starting_service(self) -> None:
        result = subprocess.run(
            ["bash", str(INSTALLER), "--dry-run", "--no-start"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

        output = result.stdout
        self.assertIn("apt-get install", output)
        self.assertIn("rsync", output)
        self.assertIn("rpi-rgb-led-matrix.git@51d3231e", output)
        self.assertIn("pip install --editable /opt/mta-board", output)
        self.assertIn("systemctl enable mta-board.service", output)
        self.assertNotIn("systemctl restart mta-board.service", output)

    def test_unknown_option_fails(self) -> None:
        result = subprocess.run(
            ["bash", str(INSTALLER), "--not-an-option"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

        self.assertEqual(2, result.returncode)
        self.assertIn("Unknown option", result.stderr)


if __name__ == "__main__":
    unittest.main()
