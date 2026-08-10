from __future__ import unicode_literals

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from driving_school.api import (
	get_instructor_dashboard,
	register_learner,
	submit_enquiry,
	update_lesson_status,
)
from driving_school.tests.helpers import make_instructor, make_learner, make_vehicle


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
		# Portal home page so learners never land on the desk after login
		self.assertEqual(frappe.db.get_value("User", email, "home_page"), "/portal-home")

	def test_register_learner_requires_valid_email(self):
		with self.assertRaises(frappe.ValidationError):
			register_learner("Bad Email", "9812345678", "not-an-email", "Car")


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
