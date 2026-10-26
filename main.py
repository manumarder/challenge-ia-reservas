"""Command-line interface for laboratory reservations."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

from reservas import (
    RESERVATIONS_PATH,
    ReservationError,
    ReservationService,
    load_inventory,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reservas de equipos de laboratorio")
    parser.add_argument(
        "--data",
        type=Path,
        default=RESERVATIONS_PATH,
        help="Archivo JSON de persistencia (por defecto: data/reservations.json)",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("inventory", help="Mostrar el inventario precargado")

    availability = commands.add_parser("availability", help="Consultar disponibilidad")
    availability.add_argument("unit_id")
    availability.add_argument("start", help="Inicio: YYYY-MM-DDTHH:MM")
    availability.add_argument("end", help="Fin: YYYY-MM-DDTHH:MM")

    reserve = commands.add_parser("reserve", help="Crear una reserva")
    reserve.add_argument("unit_id")
    reserve.add_argument("requester")
    reserve.add_argument("start", help="Inicio: YYYY-MM-DDTHH:MM")
    reserve.add_argument("end", help="Fin: YYYY-MM-DDTHH:MM")

    cancel = commands.add_parser("cancel", help="Cancelar conservando el historial")
    cancel.add_argument("reservation_id")
    commands.add_parser("reservations", help="Listar reservas e historial")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    try:
        if arguments.command == "inventory":
            result = load_inventory()
        else:
            service = ReservationService(reservations_path=arguments.data)
            if arguments.command == "availability":
                result = {
                    "unit_id": arguments.unit_id,
                    "start": arguments.start,
                    "end": arguments.end,
                    "available": service.is_available(
                        arguments.unit_id, arguments.start, arguments.end
                    ),
                }
            elif arguments.command == "reserve":
                result = asdict(
                    service.create_reservation(
                        arguments.unit_id,
                        arguments.requester,
                        arguments.start,
                        arguments.end,
                    )
                )
            elif arguments.command == "cancel":
                result = asdict(service.cancel_reservation(arguments.reservation_id))
            else:
                result = [asdict(reservation) for reservation in service.reservations]
    except ReservationError as error:
        parser.exit(2, f"Error: {error}\n")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())