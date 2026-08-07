"""Optional demo data for the Driving School app.

Run from the bench console:

	bench --site <your-site> execute driving_school.demo.create_demo_data
"""

from __future__ import unicode_literals

import frappe
from frappe.utils import add_days, flt, nowdate


def create_demo_data():
	"""Create a small set of demo records (skips anything that already exists)."""
	created = []

	branch = _get_or_create_branch(created)
	instructor = _get_or_create_instructor(created)
	vehicle = _get_or_create_vehicle(created)
	learner = _get_or_create_learner(created)
	package = _get_or_create_package(learner, created)
	_create_mock_questions(created)
	_create_lesson_booking(learner, instructor, vehicle, package, created)

	if created:
		print("Created: " + ", ".join(created))
		print("\nLogin for the demo learner (reset password via /forgot-password): " + DEMO_EMAIL)
	else:
		print("Demo data already present - nothing created.")


DEMO_EMAIL = "learner.demo@example.com"


def _get_or_create_branch(created):
	if frappe.db.exists("Driving School Branch", "BR-0001"):
		return "BR-0001"
	doc = frappe.get_doc(
		{
			"doctype": "Driving School Branch",
			"branch_name": "Main Branch",
			"city": "Demo City",
			"phone": "555-0100",
			"email": "school@example.com",
			"is_active": 1,
		}
	).insert(ignore_permissions=True)
	created.append("Branch " + doc.name)
	return doc.name


def _get_or_create_instructor(created):
	if frappe.db.exists("Driving Instructor", "INS-0001"):
		return "INS-0001"
	doc = frappe.get_doc(
		{
			"doctype": "Driving Instructor",
			"instructor_name": "Ravi Kumar",
			"mobile_number": "555-0101",
			"email": "ravi@example.com",
			"license_number": "DL-DEMO-001",
			"license_valid_upto": add_days(nowdate(), 365),
			"employment_status": "Active",
			"is_active": 1,
			"categories": [{"category": "Car", "years_experience": 5}],
		}
	).insert(ignore_permissions=True)
	created.append("Instructor " + doc.name)
	return doc.name


def _get_or_create_vehicle(created):
	if frappe.db.exists("Driving Vehicle", "VH-0001"):
		return "VH-0001"
	doc = frappe.get_doc(
		{
			"doctype": "Driving Vehicle",
			"vehicle_number": "DEMO-01-AB",
			"vehicle_model": "Demo Car 2024",
			"vehicle_type": "Car",
			"transmission": "Manual",
			"fuel_type": "Petrol",
			"insurance_expiry": add_days(nowdate(), 180),
			"status": "Available",
			"is_active": 1,
		}
	).insert(ignore_permissions=True)
	created.append("Vehicle " + doc.name)
	return doc.name


def _get_or_create_learner(created):
	if frappe.db.exists("Learner", {"email": DEMO_EMAIL}):
		return frappe.db.get_value("Learner", {"email": DEMO_EMAIL}, "name")
	doc = frappe.get_doc(
		{
			"doctype": "Learner",
			"learner_name": "Demo Learner",
			"mobile_number": "555-0102",
			"email": DEMO_EMAIL,
			"category": "Car",
			"status": "Registered",
			"training_stage": "Not Started",
			"source": "Website",
			"documents": [{"doc_type": "ID Proof", "doc_number": "ID-DEMO-001", "is_verified": 1}],
		}
	).insert(ignore_permissions=True)
	created.append("Learner " + doc.name)
	return doc.name


def _get_or_create_package(learner, created):
	existing = frappe.db.get_value("Learner Package", {"learner": learner}, "name")
	if existing:
		return existing
	doc = frappe.get_doc(
		{
			"doctype": "Learner Package",
			"learner": learner,
			"package_name": "Starter Car Package",
			"license_category": "Car",
			"lessons_count": 10,
			"theory_class_hours": 5,
			"test_attempts_included": 1,
			"validity_days": 90,
			"amount": 5000,
			"discount_amount": 500,
			"status": "Active",
			"is_active": 1,
		}
	).insert(ignore_permissions=True)
	frappe.get_doc(
		{
			"doctype": "Learner Payment",
			"learner": learner,
			"package": doc.name,
			"payment_date": nowdate(),
			"amount": doc.discounted_amount,
			"mode_of_payment": "Cash",
			"payment_type": "Package Fee",
			"status": "Received",
		}
	).insert(ignore_permissions=True)
	created.append("Package " + doc.name)
	return doc.name


def _create_mock_questions(created):
	if frappe.db.count("Mock Test Question"):
		return
	questions = [
		{
			"question": "What does a red traffic light mean?",
			"topic": "Traffic Signals",
			"option_a": "Go",
			"option_b": "Stop",
			"option_c": "Slow down",
			"option_d": "Honk and proceed",
			"correct_answer": "B",
			"explanation": "A red light means you must stop completely.",
		},
		{
			"question": "What is the maximum speed limit in a residential area?",
			"topic": "Speed Limits",
			"option_a": "20 km/h",
			"option_b": "30 km/h",
			"option_c": "50 km/h",
			"option_d": "70 km/h",
			"correct_answer": "C",
			"explanation": "Typically 50 km/h unless posted otherwise.",
		},
		{
			"question": "When should you use your indicator?",
			"topic": "Signals",
			"option_a": "Only when turning",
			"option_b": "When changing lanes or turning",
			"option_c": "Never",
			"option_d": "Only at night",
			"correct_answer": "B",
			"explanation": "Signal before turning and changing lanes.",
		},
		{
			"question": "What should you do at a yellow flashing light?",
			"topic": "Traffic Signals",
			"option_a": "Stop completely",
			"option_b": "Proceed with caution",
			"option_c": "Speed up",
			"option_d": "Reverse",
			"correct_answer": "B",
			"explanation": "A flashing yellow means proceed with caution.",
		},
		{
			"question": "A safe following distance is at least how many seconds behind the car ahead?",
			"topic": "Safe Driving",
			"option_a": "1 second",
			"option_b": "2 seconds",
			"option_c": "3 seconds",
			"option_d": "10 seconds",
			"correct_answer": "C",
			"explanation": "The 3-second rule is the recommended minimum.",
		},
	]
	for q in questions:
		frappe.get_doc({"doctype": "Mock Test Question", "category": "Car", "is_active": 1, **q}).insert(
			ignore_permissions=True
		)
	created.append("5 Mock Test Questions")


def _create_lesson_booking(learner, instructor, vehicle, package, created):
	existing = frappe.db.get_value(
		"Lesson Booking", {"learner": learner, "status": ["in", ["Requested", "Confirmed"]]}, "name"
	)
	if existing:
		return
	doc = frappe.get_doc(
		{
			"doctype": "Lesson Booking",
			"learner": learner,
			"package": package,
			"instructor": instructor,
			"vehicle": vehicle,
			"lesson_date": add_days(nowdate(), 2),
			"start_time": "10:00:00",
			"status": "Confirmed",
		}
	).insert(ignore_permissions=True)
	created.append("Lesson Booking " + doc.name)
