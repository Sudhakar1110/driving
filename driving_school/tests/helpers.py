from __future__ import unicode_literals

import frappe
from frappe.utils import nowdate


def make_learner(name="Test Learner", category="Car"):
	# No email on purpose: sync_portal_user skips learners without an email,
	# keeping the tests free of portal User creation side effects.
	return frappe.get_doc(
		{
			"doctype": "Learner",
			"learner_name": name,
			"mobile_number": "99" + frappe.generate_hash("", 8)[:8],
			"category": category,
			"status": "Registered",
			"training_stage": "Not Started",
		}
	).insert(ignore_permissions=True)


def make_instructor(categories=None):
	return frappe.get_doc(
		{
			"doctype": "Driving Instructor",
			"instructor_name": "Test Instructor " + frappe.generate_hash("", 4),
			"license_number": "DL-TEST-" + frappe.generate_hash("", 6),
			"employment_status": "Active",
			"is_active": 1,
			"categories": [{"category": c} for c in (categories or [])],
		}
	).insert(ignore_permissions=True)


def make_vehicle():
	return frappe.get_doc(
		{
			"doctype": "Driving Vehicle",
			"vehicle_number": "VH-" + frappe.generate_hash("", 5).upper(),
			"vehicle_type": "Car",
			"status": "Available",
			"is_active": 1,
		}
	).insert(ignore_permissions=True)


def make_package(learner, lessons=10, theory_hours=5, attempts=2, paid=True):
	"""Create a fully paid active package so bookings pass the balance check."""
	doc = frappe.get_doc(
		{
			"doctype": "Learner Package",
			"learner": learner.name,
			"package_name": "Test Package " + frappe.generate_hash("", 4),
			"license_category": learner.category,
			"lessons_count": lessons,
			"theory_class_hours": theory_hours,
			"test_attempts_included": attempts,
			"validity_days": 90,
			"amount": 1000,
			"status": "Active",
			"is_active": 1,
		}
	).insert(ignore_permissions=True)

	if paid:
		frappe.get_doc(
			{
				"doctype": "Learner Payment",
				"learner": learner.name,
				"package": doc.name,
				"payment_date": nowdate(),
				"amount": doc.discounted_amount,
				"mode_of_payment": "Cash",
				"payment_type": "Package Fee",
				"status": "Received",
			}
		).insert(ignore_permissions=True)
	return doc


def set_limits(max_per_week=3, min_gap=0):
	"""Set booking limits for the current test (rolled back automatically)."""
	frappe.db.set_single_value("Driving School Settings", "max_lessons_per_week", max_per_week)
	frappe.db.set_single_value("Driving School Settings", "min_gap_days_between_lessons", min_gap)
