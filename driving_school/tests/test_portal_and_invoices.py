from __future__ import unicode_literals

import datetime

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from driving_school.api import (
	get_available_slots,
	get_class_schedules,
	get_instructor_dashboard,
	register_learner,
	request_payment,
	submit_enquiry,
	update_lesson_status,
)
from driving_school.tests.helpers import make_instructor, make_learner, make_vehicle
from driving_school.utils import get_learner_for_context, to_time


class TestPublicForms(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Guest")

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def test_submit_enquiry_creates_lead(self):
		result = submit_enquiry("Lead Person", "9876543210", "Car", email="lead@example.test")
		self.assertTrue(frappe.db.exists("Enquiry", result["name"]))
		enquiry = frappe.get_doc("Enquiry", result["name"])
		self.assertEqual(enquiry.status, "New")
		self.assertEqual(enquiry.source, "Website")
		self.assertEqual(enquiry.category_of_interest, "Car")

	def test_submit_enquiry_requires_mobile(self):
		with self.assertRaises(frappe.ValidationError):
			submit_enquiry("Lead Person", "", "Car")

	def test_register_learner_creates_learner_and_user(self):
		email = "new.learner.{0}@example.test".format(frappe.generate_hash("", 6))
		result = register_learner("New Learner", "9812345678", email, "Car", password="Secret@123")
		self.assertTrue(frappe.db.exists("Learner", result["name"]))
		self.assertTrue(frappe.db.exists("User", email))
		user = frappe.get_doc("User", email)
		self.assertTrue(any(r.role == "Learner" for r in user.roles))
		# Portal home page so learners never land on the desk after login.
		# Frappe v15 removed User.home_page - it is applied at the Role level.
		self.assertEqual(frappe.db.get_value("Role", "Learner", "home_page"), "/portal-home")

	def test_register_learner_requires_valid_email(self):
		with self.assertRaises(frappe.ValidationError):
			register_learner("Bad Email", "9812345678", "not-an-email", "Car")

	def test_portal_api_methods_are_guest_accessible(self):
		"""Regression: Frappe v15.100+ only lets Guests call methods marked
		allow_guest=True - without it every portal API 403s in public demo mode
		(e.g. empty time-slot grid, register button, mock test submit)."""
		import driving_school.api as api

		for name in (
			"get_learner_summary",
			"get_resources",
			"get_available_slots",
			"book_lesson",
			"cancel_lesson",
			"reschedule_lesson",
			"get_my_lessons",
			"get_my_payments",
			"request_payment",
			"get_my_progress",
			"get_mock_questions",
			"submit_mock_test",
			"submit_feedback",
			"submit_enquiry",
			"register_learner",
			"get_class_schedules",
		):
			self.assertIn(
				getattr(api, name),
				frappe.guest_methods,
				"{0} must be guest-accessible (allow_guest=True)".format(name),
			)

	def test_instructor_apis_are_not_guest_accessible(self):
		"""Instructor-only methods must stay login-gated."""
		import driving_school.api as api

		for name in ("get_instructor_dashboard", "update_lesson_status", "request_instructor_leave"):
			self.assertNotIn(getattr(api, name), frappe.guest_methods)

	def test_logged_in_user_auto_creates_learner_profile(self):
		"""No manual linking needed: the portal creates a Learner for the user."""
		frappe.set_user("Administrator")
		name, display = get_learner_for_context()
		self.assertTrue(name)
		self.assertEqual(frappe.db.get_value("Learner", name, "email"), "Administrator")
		# second call reuses the same profile
		self.assertEqual(get_learner_for_context()[0], name)

	def test_learner_desk_save_with_existing_user_does_not_crash(self):
		"""Saving a Learner in the desk whose email matches an existing user must
		not crash (regression: User.home_page was removed in Frappe v15)."""
		email = "desk.save.{0}@example.test".format(frappe.generate_hash("", 6))
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": "Desk Save", "send_welcome_email": False}
		).insert(ignore_permissions=True)

		learner = frappe.get_doc(
			{
				"doctype": "Learner",
				"learner_name": "Desk Save Learner",
				"mobile_number": "9876543211",
				"email": email,
				"status": "Registered",
			}
		)
		learner.insert(ignore_permissions=True)  # triggers sync_portal_user
		learner.learner_name = "Desk Save Learner 2"
		learner.save(ignore_permissions=True)  # on_update -> sync_portal_user again
		self.assertTrue(frappe.db.exists("Learner", learner.name))
		user = frappe.get_doc("User", email)
		self.assertTrue(any(r.role == "Learner" for r in user.roles))


class TestInstructorPortal(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.instructor = make_instructor()
		self.vehicle = make_vehicle()

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def _make_booking(self, learner, day=None):
		return frappe.get_doc(
			{
				"doctype": "Lesson Booking",
				"learner": learner.name,
				"instructor": self.instructor.name,
				"vehicle": self.vehicle.name,
				"lesson_date": day or nowdate(),
				"start_time": "23:30:00",
				"status": "Confirmed",
				"lesson_fee": 100,
			}
		).insert(ignore_permissions=True)

	def test_dashboard_requires_instructor_link(self):
		# Administrator is not linked to an instructor profile
		with self.assertRaises(frappe.PermissionError):
			get_instructor_dashboard()

	def test_unlinked_user_cannot_update_lesson_status(self):
		booking = self._make_booking(make_learner("Owner Learner"))
		with self.assertRaises(frappe.PermissionError):
			update_lesson_status(booking.name, "Completed")

	def test_instructor_can_mark_lesson_completed(self):
		email = "instructor.{0}@example.test".format(frappe.generate_hash("", 6))
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": "Test Instructor", "send_welcome_email": False}
		).insert(ignore_permissions=True)
		frappe.db.set_value("Driving Instructor", self.instructor.name, "user", email)

		booking = self._make_booking(make_learner("Owner Learner"))
		frappe.set_user(email)

		result = update_lesson_status(booking.name, "Completed", instructor_notes="Good progress")
		self.assertEqual(result["status"], "Completed")
		self.assertEqual(
			frappe.db.get_value("Lesson Booking", booking.name, "instructor_notes"),
			"Good progress",
		)

	def test_future_lesson_cannot_be_updated(self):
		email = "instructor.future.{0}@example.test".format(frappe.generate_hash("", 6))
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": "Test Instructor", "send_welcome_email": False}
		).insert(ignore_permissions=True)
		frappe.db.set_value("Driving Instructor", self.instructor.name, "user", email)
		frappe.set_user(email)

		booking = self._make_booking(make_learner("Future Learner"), day=add_days(nowdate(), 3))
		with self.assertRaises(frappe.ValidationError):
			update_lesson_status(booking.name, "Completed")


class TestSalesInvoiceBridge(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.learner = make_learner("Invoice Learner")

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def test_package_amount_overflow_gives_friendly_error(self):
		"""Regression: an absurd amount used to crash with a raw DB DataError
		('Out of range value for column amount') - now a clear ValidationError."""
		with self.assertRaises(frappe.ValidationError) as ctx:
			frappe.get_doc(
				{
					"doctype": "Learner Package",
					"learner": self.learner.name,
					"package_name": "Overflow Pkg",
					"license_category": "Car",
					"lessons_count": 10,
					"amount": 11000000000000000000,
					"status": "Active",
					"is_active": 1,
				}
			).insert(ignore_permissions=True)
		self.assertIn("too large", str(ctx.exception))

	def test_negative_amount_gives_friendly_error(self):
		with self.assertRaises(frappe.ValidationError) as ctx:
			frappe.get_doc(
				{
					"doctype": "Learner Package",
					"learner": self.learner.name,
					"package_name": "Neg Pkg",
					"license_category": "Car",
					"lessons_count": 10,
					"amount": -100,
					"status": "Active",
					"is_active": 1,
				}
			).insert(ignore_permissions=True)
		self.assertIn("cannot be negative", str(ctx.exception))

	def test_package_less_payment_request_succeeds(self):
		"""Learners without an active package can still record a payment request
		(registration fee, add-on lessons, etc.) - no hard gate."""
		frappe.set_user("Guest")
		result = request_payment(
			amount=500, mode_of_payment="UPI", payment_type="Other", reference_number="TXN-DEMO-1"
		)
		self.assertTrue(frappe.db.exists("Learner Payment", result["name"]))
		payment = frappe.get_doc("Learner Payment", result["name"])
		self.assertIsNone(payment.package)
		self.assertEqual(payment.payment_type, "Other")
		self.assertEqual(payment.status, "Requested")

	def test_payment_request_rejects_invalid_type(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.ValidationError):
			request_payment(amount=100, mode_of_payment="Cash", payment_type="Nonsense")

	def test_payment_request_rejects_zero_amount(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.ValidationError):
			request_payment(amount=0, mode_of_payment="Cash")

	def test_received_payment_does_not_break_without_erpnext(self):
		"""The invoice bridge must be a no-op (never crash) without ERPNext."""
		package = frappe.get_doc(
			{
				"doctype": "Learner Package",
				"learner": self.learner.name,
				"package_name": "Invoice Test Pkg",
				"license_category": "Car",
				"lessons_count": 10,
				"amount": 1000,
				"status": "Active",
				"is_active": 1,
			}
		).insert(ignore_permissions=True)

		payment = frappe.get_doc(
			{
				"doctype": "Learner Payment",
				"learner": self.learner.name,
				"package": package.name,
				"payment_date": nowdate(),
				"amount": 1000,
				"mode_of_payment": "Cash",
				"payment_type": "Package Fee",
				"status": "Received",
			}
		).insert(ignore_permissions=True)

		self.assertEqual(payment.status, "Received")
		self.assertEqual(
			frappe.db.get_value("Learner Package", package.name, "balance_amount"), 0
		)


class TestToTimeRobustness(IntegrationTestCase):
	"""Regression: unparseable business-hour settings crashed the slot APIs
	(TypeError: combine() argument 2 must be datetime.time, not str)."""

	def test_parses_common_formats(self):
		self.assertEqual(to_time("09:00:00"), datetime.time(9, 0))
		self.assertEqual(to_time("9:00"), datetime.time(9, 0))
		self.assertEqual(to_time("9.00"), datetime.time(9, 0))
		self.assertEqual(to_time("9:00 AM"), datetime.time(9, 0))
		self.assertEqual(to_time("2026-08-10 09:00:00"), datetime.time(9, 0))
		self.assertEqual(to_time(datetime.timedelta(hours=9)), datetime.time(9, 0))

	def test_unparseable_returns_none(self):
		self.assertIsNone(to_time("garbage"))
		self.assertIsNone(to_time(""))
		self.assertIsNone(to_time(None))

	def test_slots_work_with_messy_business_hours(self):
		"""Slot generation must fall back to defaults instead of crashing."""
		settings = frappe.get_single("Driving School Settings")
		settings.business_start_time = "9.00"
		settings.business_end_time = "17.00"
		settings.lesson_duration_minutes = 60
		settings.save(ignore_permissions=True)

		# Guest access resolves to the demo (first) learner - ensure one exists
		make_learner("Settings Slot Learner")
		frappe.set_user("Guest")
		slots = get_available_slots(lesson_date=add_days(nowdate(), 1))
		self.assertTrue(slots)
		self.assertTrue(any(s["available"] for s in slots))

	def test_booked_slot_is_unavailable_when_resource_selected(self):
		"""Regression: TIME key normalisation - the MariaDB driver returns
		timedelta ('9:00:00', unpadded) which used to mismatch the zero-padded
		slot keys ('09:00:00'), so booked slots looked available."""
		settings = frappe.get_single("Driving School Settings")
		settings.business_start_time = "09:00:00"
		settings.business_end_time = "10:00:00"
		settings.lesson_duration_minutes = 60
		settings.save(ignore_permissions=True)

		learner = make_learner("Key Normalise Learner")
		instructor = make_instructor(["Car"])
		vehicle = make_vehicle()
		frappe.get_doc(
			{
				"doctype": "Lesson Booking",
				"learner": learner.name,
				"instructor": instructor.name,
				"vehicle": vehicle.name,
				"lesson_date": add_days(nowdate(), 1),
				"start_time": "09:00:00",
				"status": "Confirmed",
			}
		).insert(ignore_permissions=True)

		frappe.set_user("Guest")
		slots = get_available_slots(
			lesson_date=add_days(nowdate(), 1),
			instructor=instructor.name,
			vehicle=vehicle.name,
		)
		self.assertEqual(len(slots), 1)
		self.assertFalse(slots[0]["available"])


class TestClassSchedules(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.instructor = make_instructor(["Car"])
		self.vehicle = make_vehicle()

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def test_schedules_include_theory_classes_and_slots(self):
		tomorrow = add_days(nowdate(), 1)
		frappe.get_doc(
			{
				"doctype": "Theory Class",
				"title": "Road Rules",
				"class_date": tomorrow,
				"start_time": "10:00:00",
				"end_time": "11:00:00",
				"instructor": self.instructor.name,
				"status": "Scheduled",
			}
		).insert(ignore_permissions=True)

		frappe.set_user("Guest")
		result = get_class_schedules(days=7)
		self.assertTrue(any(tc["title"] == "Road Rules" for tc in result["theory_classes"]))
		self.assertEqual(len(result["days"]), 7)
		self.assertTrue(all(len(d["slots"]) > 0 for d in result["days"]))
		self.assertTrue(all("start_time" in s for d in result["days"] for s in d["slots"]))

	def test_booked_slot_is_marked_unavailable(self):
		tomorrow = add_days(nowdate(), 1)
		learner = make_learner("Slot Learner")
		frappe.get_doc(
			{
				"doctype": "Lesson Booking",
				"learner": learner.name,
				"instructor": self.instructor.name,
				"vehicle": self.vehicle.name,
				"lesson_date": tomorrow,
				"start_time": "09:00:00",
				"status": "Confirmed",
			}
		).insert(ignore_permissions=True)

		frappe.set_user("Guest")
		result = get_class_schedules(days=7)
		day = next(d for d in result["days"] if d["date"] == tomorrow.strftime("%Y-%m-%d"))
		slot = next(s for s in day["slots"] if s["start_time"] == "09:00:00")
		self.assertFalse(slot["available"])
