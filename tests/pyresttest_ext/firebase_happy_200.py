from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import firebase_admin
from firebase_admin import credentials, firestore

from .runner import run_many_files


TEST_DOCTOR_ID = "hC1kDpvF7It8suxOayV9"
ASSIGN_APPOINTMENT_ID = "test_e2e_assign_same_doctor"
COMPLETE_APPOINTMENT_ID = "test_e2e_complete_appointment"
WEBHOOK_SESSION_APPOINTMENT_ID = "test-happy-200-session"
TEST_APPOINTMENT_IDS = [
    ASSIGN_APPOINTMENT_ID,
    COMPLETE_APPOINTMENT_ID,
    WEBHOOK_SESSION_APPOINTMENT_ID,
]


def get_db() -> firestore.Client:
    if not firebase_admin._apps:
        cred = credentials.Certificate("serviceAccount.json")
        firebase_admin.initialize_app(cred)
    return firestore.client()


def _appointment_payload(patient_name: str, doctor_id: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "patientName": patient_name,
        "email": "test-happy-200@example.com",
        "phone": "0123456789",
        "sdt": "0123456789",
        "date": "2099-12-30",
        "time": "10:00",
        "day": "Thu 4",
        "service": "Nho rang",
        "note": "Created by automated happy_200 test",
        "verified": True,
        "createdAt": datetime.now().isoformat(),
        "expiresAt": (datetime.now() + timedelta(hours=24)).isoformat(),
        "testRun": True,
    }
    if doctor_id:
        payload["doctorID"] = doctor_id
    return payload


def seed() -> None:
    db = get_db()
    doctor = db.collection("doctors").document(TEST_DOCTOR_ID).get()
    if not doctor.exists:
        raise RuntimeError(f"Test doctor does not exist: {TEST_DOCTOR_ID}")

    db.collection("appointments").document(ASSIGN_APPOINTMENT_ID).set(
        _appointment_payload("Test Assign Same Doctor", doctor_id=TEST_DOCTOR_ID)
    )
    db.collection("appointments").document(COMPLETE_APPOINTMENT_ID).set(
        _appointment_payload("Test Complete Appointment", doctor_id=TEST_DOCTOR_ID)
    )


def cleanup() -> None:
    db = get_db()
    for appointment_id in TEST_APPOINTMENT_IDS:
        db.collection("appointments").document(appointment_id).delete()

    for appointment_id in TEST_APPOINTMENT_IDS:
        bills = db.collection("bills").where("appointmentId", "==", appointment_id).stream()
        for bill in bills:
            bill.reference.delete()


def run(base_url: str, report: Path | None = None, keep_data: bool = False) -> int:
    seed()
    try:
        payload = run_many_files(
            [Path("tests/pyresttest/happy_200_suite.yaml")],
            base_url=base_url,
            mode="sync",
            file_concurrency=1,
        )
        if report:
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

        summary = payload["summary"]
        print(
            f"{summary['passed']}/{summary['total']} passed, "
            f"failed={summary['failed']}, wall_time_ms={summary['wall_time_ms']:.1f}, "
            f"p95_ms={summary['p95_ms']}"
        )
        if report:
            print(f"Report: {report}")
        return 1 if summary["failed"] else 0
    finally:
        if not keep_data:
            cleanup()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Seed, run, and cleanup Firebase-backed happy-path 200 tests")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("seed", help="Create deterministic Firebase test documents")
    subparsers.add_parser("cleanup", help="Delete deterministic Firebase test documents and generated bills")

    run_parser = subparsers.add_parser("run", help="Seed, run happy_200_suite.yaml, then cleanup")
    run_parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    run_parser.add_argument("--report", type=Path, default=Path("tests/reports/happy_200_report.json"))
    run_parser.add_argument("--keep-data", action="store_true", help="Do not cleanup seeded/generated test data")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "seed":
        seed()
        print("Seeded happy-path Firebase test data.")
        return 0
    if args.command == "cleanup":
        cleanup()
        print("Cleaned happy-path Firebase test data.")
        return 0
    if args.command == "run":
        return run(args.base_url, args.report, args.keep_data)
    raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
