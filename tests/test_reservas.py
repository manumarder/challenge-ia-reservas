import tempfile
import unittest
import json
from pathlib import Path
import subprocess
import sys

from reservas import ReservationError, ReservationService


INVENTORY = {
    "MIC-01": "Microscopio digital",
    "MIC-02": "Microscopio digital",
    "OSC-01": "Osciloscopio",
    "MUL-01": "Multímetro",
    "FUE-01": "Fuente de alimentación",
}


class ReservationServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.reservations_path = Path(self.temporary_directory.name) / "reservations.json"
        self.service = ReservationService(INVENTORY, self.reservations_path)

    def reserve(self, unit: str = "MIC-01", start: str = "2026-11-02T10:00", end: str = "2026-11-02T11:00"):
        return self.service.create_reservation(unit, "Ada Lovelace", start, end)

    def test_creates_valid_reservation(self) -> None:
        reservation = self.reserve()
        self.assertEqual(reservation.status, "active")
        self.assertTrue(reservation.id)

    def test_rejects_overlapping_reservation(self) -> None:
        self.reserve()
        with self.assertRaises(ReservationError):
            self.reserve(start="2026-11-02T10:30", end="2026-11-02T11:30")

    def test_allows_consecutive_reservations(self) -> None:
        self.reserve()
        following = self.reserve(start="2026-11-02T11:00", end="2026-11-02T12:00")
        self.assertEqual(following.status, "active")

    def test_allows_different_units_at_the_same_time(self) -> None:
        self.reserve()
        other_unit = self.reserve(unit="MIC-02")
        self.assertEqual(other_unit.unit_id, "MIC-02")

    def test_availability_uses_active_interval_rules(self) -> None:
        self.reserve()

        self.assertFalse(
            self.service.is_available("MIC-01", "2026-11-02T10:30", "2026-11-02T11:30")
        )
        self.assertTrue(
            self.service.is_available("MIC-01", "2026-11-02T11:00", "2026-11-02T12:00")
        )
        self.assertTrue(
            self.service.is_available("MIC-02", "2026-11-02T10:00", "2026-11-02T11:00")
        )

    def test_rejects_invalid_inputs(self) -> None:
        invalid_requests = [
            ("UNKNOWN", "Ada", "2026-11-02T10:00", "2026-11-02T11:00"),
            ("MIC-01", "   ", "2026-11-02T10:00", "2026-11-02T11:00"),
            ("MIC-01", "Ada", "2026-02-30T10:00", "2026-11-02T11:00"),
            ("MIC-01", "Ada", "2026-11-02T11:00", "2026-11-02T11:00"),
            ("MIC-01", "Ada", "2026-11-02T12:00", "2026-11-02T11:00"),
        ]
        for unit, requester, start, end in invalid_requests:
            with self.subTest(unit=unit, requester=requester, start=start, end=end):
                with self.assertRaises(ReservationError):
                    self.service.create_reservation(unit, requester, start, end)

    def test_cancellation_keeps_record_and_releases_interval(self) -> None:
        original = self.reserve()
        cancelled = self.service.cancel_reservation(original.id)
        replacement = self.reserve()

        self.assertEqual(cancelled.id, original.id)
        self.assertEqual(cancelled.requester, original.requester)
        self.assertEqual(cancelled.status, "cancelled")
        self.assertEqual(len(self.service.reservations), 2)
        self.assertEqual(replacement.status, "active")

    def test_active_and_cancelled_reservations_survive_restart(self) -> None:
        active = self.reserve()
        cancelled = self.reserve(unit="MIC-02")
        self.service.cancel_reservation(cancelled.id)

        restarted = ReservationService(INVENTORY, self.reservations_path)

        self.assertEqual([item.id for item in restarted.reservations], [active.id, cancelled.id])
        self.assertEqual(restarted.reservations[0].status, "active")
        self.assertEqual(restarted.reservations[1].status, "cancelled")
        self.assertFalse(restarted.is_available("MIC-01", active.start, active.end))
        self.assertTrue(restarted.is_available("MIC-02", cancelled.start, cancelled.end))

    def test_active_and_cancelled_reservations_survive_process_restart(self) -> None:
        project_root = Path(__file__).resolve().parents[1]

        def run_cli(*arguments: str) -> str:
            result = subprocess.run(
                [
                    sys.executable,
                    str(project_root / "main.py"),
                    "--data",
                    str(self.reservations_path),
                    *arguments,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            return result.stdout

        active = json.loads(
            run_cli("reserve", "MIC-01", "Ada Lovelace", "2026-11-02T10:00", "2026-11-02T11:00")
        )
        cancelled = json.loads(
            run_cli("reserve", "MIC-02", "Grace Hopper", "2026-11-02T10:00", "2026-11-02T11:00")
        )
        run_cli("cancel", cancelled["id"])
        reservations = json.loads(run_cli("reservations"))

        self.assertEqual([item["id"] for item in reservations], [active["id"], cancelled["id"]])
        self.assertEqual([item["status"] for item in reservations], ["active", "cancelled"])


if __name__ == "__main__":
    unittest.main()