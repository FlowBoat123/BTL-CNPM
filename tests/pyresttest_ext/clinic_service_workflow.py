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
TEST_DOCTOR_NO_CALENDAR_ID = "test_e2e_doctor_no_calendar"
ASSIGN_APPOINTMENT_ID = "test_e2e_assign_same_doctor"
ASSIGN_UNASSIGNED_APPOINTMENT_ID = "test_e2e_assign_unassigned"
COMPLETE_APPOINTMENT_ID = "test_e2e_complete_appointment"
COMPLETE_MULTI_SERVICE_APPOINTMENT_ID = "test_e2e_complete_multi_service"
WEBHOOK_SESSION_APPOINTMENT_ID = "test-clinic-workflow-session"
DUPLICATE_SLOT_SESSION_ID = "test-clinic-workflow-duplicate-slot"
STRING_NAME_SESSION_ID = "test-clinic-workflow-string-name"
TEST_APPOINTMENT_IDS = [
    ASSIGN_APPOINTMENT_ID,
    ASSIGN_UNASSIGNED_APPOINTMENT_ID,
    COMPLETE_APPOINTMENT_ID,
    COMPLETE_MULTI_SERVICE_APPOINTMENT_ID,
    WEBHOOK_SESSION_APPOINTMENT_ID,
    DUPLICATE_SLOT_SESSION_ID,
    STRING_NAME_SESSION_ID,
]


def get_db() -> firestore.Client:
    if not firebase_admin._apps:
        cred = credentials.Certificate("serviceAccount.json")
        firebase_admin.initialize_app(cred)
    return firestore.client()


def _appointment_payload(patient_name: str, doctor_id: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "patientName": patient_name,
        "email": "test-clinic-workflow@example.com",
        "phone": "0123456789",
        "sdt": "0123456789",
        "date": "2099-12-30",
        "time": "10:00",
        "day": "Thu 4",
        "service": "Nho rang",
        "note": "Created by automated clinic service workflow test",
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
    cleanup()
    doctor = db.collection("doctors").document(TEST_DOCTOR_ID).get()
    if not doctor.exists:
        raise RuntimeError(f"Test doctor does not exist: {TEST_DOCTOR_ID}")

    db.collection("doctors").document(TEST_DOCTOR_NO_CALENDAR_ID).set(
        {
            "name": "Test Doctor No Calendar",
            "birthdate": "01/01/2099",
            "email": "test-doctor-no-calendar@example.com",
            "phone": "0123456789",
            "password": "test-only",
            "testRun": True,
        }
    )
    db.collection("appointments").document(ASSIGN_APPOINTMENT_ID).set(
        _appointment_payload("Test Assign Same Doctor", doctor_id=TEST_DOCTOR_ID)
    )
    db.collection("appointments").document(ASSIGN_UNASSIGNED_APPOINTMENT_ID).set(
        _appointment_payload("Test Assign Unassigned")
    )
    db.collection("appointments").document(COMPLETE_APPOINTMENT_ID).set(
        _appointment_payload("Test Complete Appointment", doctor_id=TEST_DOCTOR_ID)
    )
    db.collection("appointments").document(COMPLETE_MULTI_SERVICE_APPOINTMENT_ID).set(
        _appointment_payload("Test Complete Multi Service", doctor_id=TEST_DOCTOR_ID)
    )


def cleanup() -> None:
    db = get_db()
    for appointment_id in TEST_APPOINTMENT_IDS:
        db.collection("appointments").document(appointment_id).delete()

    for appointment_id in TEST_APPOINTMENT_IDS:
        bills = db.collection("bills").where("appointmentId", "==", appointment_id).stream()
        for bill in bills:
            bill.reference.delete()
    db.collection("doctors").document(TEST_DOCTOR_NO_CALENDAR_ID).delete()


def _bills_for_appointment(db: firestore.Client, appointment_id: str) -> list[dict[str, Any]]:
    docs = db.collection("bills").where("appointmentId", "==", appointment_id).stream()
    return [{"id": doc.id, **(doc.to_dict() or {})} for doc in docs]


def _service_price(db: firestore.Client, service_id: str) -> int:
    doc = db.collection("services").document(service_id).get()
    if not doc.exists:
        raise AssertionError(f"Required service does not exist: {service_id}")
    data = doc.to_dict() or {}
    return int(data["price"])


def validate_side_effects() -> list[str]:
    db = get_db()
    failures: list[str] = []

    assigned = db.collection("appointments").document(ASSIGN_UNASSIGNED_APPOINTMENT_ID).get()
    if not assigned.exists:
        failures.append(f"Missing appointment after assign: {ASSIGN_UNASSIGNED_APPOINTMENT_ID}")
    else:
        assigned_data = assigned.to_dict() or {}
        if assigned_data.get("doctorID") != TEST_DOCTOR_NO_CALENDAR_ID:
            failures.append(
                f"Assigned doctor mismatch: actual={assigned_data.get('doctorID')}, "
                f"expected={TEST_DOCTOR_NO_CALENDAR_ID}"
            )
        if assigned_data.get("googleEventId"):
            failures.append("Assign test unexpectedly created googleEventId")

    single_bills = _bills_for_appointment(db, COMPLETE_APPOINTMENT_ID)
    if len(single_bills) != 1:
        failures.append(f"Expected 1 bill for {COMPLETE_APPOINTMENT_ID}, found {len(single_bills)}")
    elif single_bills[0].get("totalAmount") != _service_price(db, "1"):
        failures.append(
            f"Single-service bill total mismatch: actual={single_bills[0].get('totalAmount')}, "
            f"expected={_service_price(db, '1')}"
        )

    multi_bills = _bills_for_appointment(db, COMPLETE_MULTI_SERVICE_APPOINTMENT_ID)
    expected_multi_total = _service_price(db, "1") + (_service_price(db, "10") * 2)
    if len(multi_bills) != 1:
        failures.append(
            f"Expected 1 bill for {COMPLETE_MULTI_SERVICE_APPOINTMENT_ID}, found {len(multi_bills)}"
        )
    elif multi_bills[0].get("totalAmount") != expected_multi_total:
        failures.append(
            f"Multi-service bill total mismatch: actual={multi_bills[0].get('totalAmount')}, "
            f"expected={expected_multi_total}"
        )

    completed = db.collection("appointments").document(COMPLETE_MULTI_SERVICE_APPOINTMENT_ID).get()
    if completed.exists and (completed.to_dict() or {}).get("status") != "completed":
        failures.append(f"Appointment was not marked completed: {COMPLETE_MULTI_SERVICE_APPOINTMENT_ID}")

    duplicate_slot = db.collection("appointments").document(DUPLICATE_SLOT_SESSION_ID).get()
    if duplicate_slot.exists:
        failures.append(f"Duplicate-slot webhook unexpectedly created appointment: {DUPLICATE_SLOT_SESSION_ID}")

    string_name = db.collection("appointments").document(STRING_NAME_SESSION_ID).get()
    if not string_name.exists:
        failures.append(f"String-name webhook did not create appointment: {STRING_NAME_SESSION_ID}")
    else:
        string_name_data = string_name.to_dict() or {}
        if string_name_data.get("patientName") != "Test String Name":
            failures.append(
                f"String-name patient mismatch: actual={string_name_data.get('patientName')}, "
                "expected=Test String Name"
            )
        if string_name_data.get("sdt") != "0987654321":
            failures.append(
                f"String-name phone mismatch: actual={string_name_data.get('sdt')}, "
                "expected=0987654321"
            )

    return failures


def run(base_url: str, report: Path | None = None, keep_data: bool = False) -> int:
    seed()
    try:
        payload = run_many_files(
            [Path("tests/pyresttest/clinic_service_workflow_suite.yaml")],
            base_url=base_url,
            mode="sync",
            file_concurrency=1,
        )
        if report:
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

        summary = payload["summary"]
        side_effect_failures = validate_side_effects() if summary["failed"] == 0 else []
        print(
            f"{summary['passed']}/{summary['total']} passed, "
            f"failed={summary['failed']}, wall_time_ms={summary['wall_time_ms']:.1f}, "
            f"p95_ms={summary['p95_ms']}"
        )
        if side_effect_failures:
            print("Side-effect validation failed:")
            for failure in side_effect_failures:
                print(f"  - {failure}")
        if report:
            print(f"Report: {report}")
        return 1 if summary["failed"] or side_effect_failures else 0
    finally:
        if not keep_data:
            cleanup()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Seed, run, and cleanup Firebase-backed clinic service workflow tests")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("seed", help="Create deterministic Firebase test documents")
    subparsers.add_parser("cleanup", help="Delete deterministic Firebase test documents and generated bills")

    run_parser = subparsers.add_parser("run", help="Seed, run clinic_service_workflow_suite.yaml, then cleanup")
    run_parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    run_parser.add_argument("--report", type=Path, default=Path("tests/reports/clinic_service_workflow_report.json"))
    run_parser.add_argument("--keep-data", action="store_true", help="Do not cleanup seeded/generated test data")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "seed":
        seed()
        print("Seeded clinic service workflow Firebase test data.")
        return 0
    if args.command == "cleanup":
        cleanup()
        print("Cleaned clinic service workflow Firebase test data.")
        return 0
    if args.command == "run":
        return run(args.base_url, args.report, args.keep_data)
    raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
