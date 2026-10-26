"""Reservation rules and JSON persistence for the laboratory inventory."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
INVENTORY_PATH = ROOT / "inventory.json"
RESERVATIONS_PATH = ROOT / "data" / "reservations.json"
DATETIME_FORMAT = "%Y-%m-%dT%H:%M"


class ReservationError(ValueError):
    """Raised when a reservation request violates a business rule."""


@dataclass(frozen=True)
class Reservation:
    id: str
    unit_id: str
    requester: str
    start: str
    end: str
    status: str = "active"


def parse_datetime(value: str) -> datetime:
    try:
        parsed = datetime.strptime(value, DATETIME_FORMAT)
    except (TypeError, ValueError) as error:
        raise ReservationError(
            f"Fecha y hora inválidas: {value!r}. Use YYYY-MM-DDTHH:MM."
        ) from error
    if parsed.strftime(DATETIME_FORMAT) != value:
        raise ReservationError(
            f"Formato de fecha y hora inválido: {value!r}. Use YYYY-MM-DDTHH:MM."
        )
    return parsed


class ReservationService:
    def __init__(
        self,
        inventory: dict[str, str] | None = None,
        reservations_path: Path = RESERVATIONS_PATH,
    ) -> None:
        self.inventory = inventory if inventory is not None else load_inventory()
        self.reservations_path = Path(reservations_path)
        self.reservations = self._load_reservations()

    def is_available(self, unit_id: str, start: str, end: str) -> bool:
        start_at, end_at = self._validate_request(unit_id, "consulta", start, end)
        return not any(
            reservation.status == "active"
            and reservation.unit_id == unit_id
            and start_at < parse_datetime(reservation.end)
            and parse_datetime(reservation.start) < end_at
            for reservation in self.reservations
        )

    def create_reservation(
        self, unit_id: str, requester: str, start: str, end: str
    ) -> Reservation:
        requester = requester.strip() if isinstance(requester, str) else ""
        start_at, end_at = self._validate_request(unit_id, requester, start, end)
        if not self._is_interval_available(unit_id, start_at, end_at):
            raise ReservationError(
                f"La unidad {unit_id} ya tiene una reserva activa superpuesta."
            )

        reservation = Reservation(
            id=uuid.uuid4().hex,
            unit_id=unit_id,
            requester=requester,
            start=start,
            end=end,
        )
        self.reservations.append(reservation)
        self._save_reservations()
        return reservation

    def cancel_reservation(self, reservation_id: str) -> Reservation:
        for index, reservation in enumerate(self.reservations):
            if reservation.id == reservation_id:
                if reservation.status == "cancelled":
                    raise ReservationError("La reserva ya está cancelada.")
                cancelled = Reservation(
                    id=reservation.id,
                    unit_id=reservation.unit_id,
                    requester=reservation.requester,
                    start=reservation.start,
                    end=reservation.end,
                    status="cancelled",
                )
                self.reservations[index] = cancelled
                self._save_reservations()
                return cancelled
        raise ReservationError(f"No existe la reserva {reservation_id}.")

    def _validate_request(
        self, unit_id: str, requester: str, start: str, end: str
    ) -> tuple[datetime, datetime]:
        if unit_id not in self.inventory:
            raise ReservationError(f"Unidad desconocida: {unit_id}.")
        if not requester.strip():
            raise ReservationError("El solicitante no puede estar vacío.")
        start_at = parse_datetime(start)
        end_at = parse_datetime(end)
        if start_at >= end_at:
            raise ReservationError("El inicio debe ser anterior al fin.")
        return start_at, end_at

    def _is_interval_available(
        self, unit_id: str, start_at: datetime, end_at: datetime
    ) -> bool:
        return not any(
            reservation.status == "active"
            and reservation.unit_id == unit_id
            and start_at < parse_datetime(reservation.end)
            and parse_datetime(reservation.start) < end_at
            for reservation in self.reservations
        )

    def _load_reservations(self) -> list[Reservation]:
        if not self.reservations_path.exists():
            return []
        try:
            raw_reservations = json.loads(self.reservations_path.read_text(encoding="utf-8"))
            reservations = [Reservation(**item) for item in raw_reservations]
            for reservation in reservations:
                if reservation.status not in {"active", "cancelled"}:
                    raise ValueError("estado desconocido")
            return reservations
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
            raise ReservationError(
                f"No se pudieron leer las reservas de {self.reservations_path}."
            ) from error

    def _save_reservations(self) -> None:
        self.reservations_path.parent.mkdir(parents=True, exist_ok=True)
        content = [asdict(reservation) for reservation in self.reservations]
        self.reservations_path.write_text(
            json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )


def load_inventory(path: Path = INVENTORY_PATH) -> dict[str, str]:
    try:
        inventory: Any = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReservationError(f"No se pudo leer el inventario de {path}.") from error
    if not isinstance(inventory, dict) or not inventory or not all(
        isinstance(unit_id, str) and isinstance(name, str)
        for unit_id, name in inventory.items()
    ):
        raise ReservationError("El inventario debe ser un objeto JSON de unidades.")
    return inventory