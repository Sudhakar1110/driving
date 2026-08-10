from __future__ import unicode_literals

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from driving_school.tests.helpers import make_instructor, make_learner, make_package, make_vehicle


class TestTheoryHours(IntegrationTestCase):
	def setUp(self):
		self.learner = make_learner("Theory Hours Learner")
		make_package(self.learner, theory_hours=1, attempts=2)

	def _make_class(self, title):
		return frappe.get_doc(
			{
				"doctype": "Theory Class",
				"title": title,
				"class_date": add_days(nowdate(), 1),
				"start_time": "09:00:00",
				"end_time": "10:00:00",
				"status": "Scheduled",
			}
		).insert(ignore_permissions=True)

	def _attend(self, cls, status="Present"):
		return frappe.get_doc(
			{
				"doctype": "Theory Class Attendance",
				"theory_class": cls.name,
				"learner": self.learner.name,
				"status": status,
			}
		).insert(ignore_permissions=True)

	def test_theory_hours_enforced(self):
		self._attend(self._make_class("Class 1"))  # 1 hour used, limit is 1
		with self.assertRaises(frappe.ValidationError):
			self._attend(self._make_class("Class 2"))

	def test_absent_does_not_consume_hours(self):
		self._attend(self._make_class("Class 1"))
		self._attend(self._make_class("Class 2"), status="Absent")  # no error


class TestTestAttemptsAndFailedStatus(IntegrationTestCase):
	def setUp(self):
		self.learner = make_learner("Attempts Learner")
		self.instructor = make_instructor()
		self.vehicle = make_vehicle()
		make_package(self.learner, attempts=1)

	def _make_test(self):
		return frappe.get_doc(
			{
				"doctype": "Driving Test",
				"learner": self.learner.name,
				"test_type": "Driving",
				"test_date": add_days(nowdate(), 2),
				"start_time": "10:00:00",
				"instructor": self.instructor.name,
				"vehicle": self.vehicle.name,
				"result": "Pending",
			}
		).insert(ignore_permissions=True)

	def test_test_attempts_enforced(self):
		self._make_test()
		with self.assertRaises(frappe.ValidationError):
			self._make_test()

	def test_failed_test_marks_learner_failed(self):
		test = self._make_test()
		test.result = "Fail"
		test.score = 40
		test.save(ignore_permissions=True)
		self.assertEqual(frappe.db.get_value("Learner", self.learner.name, "status"), "Failed")

	def test_passed_test_marks_learner_passed(self):
		test = self._make_test()
		test.result = "Pass"
		test.score = 90
		test.save(ignore_permissions=True)
		self.assertEqual(frappe.db.get_value("Learner", self.learner.name, "status"), "Passed")


class TestFeedback(IntegrationTestCase):
	def setUp(self):
		self.learner = make_learner("Feedback Learner")
		self.instructor = make_instructor()
		self.vehicle = make_vehicle()
		self.package = make_package(self.learner)
		self.booking = frappe.get_doc(
			{
				"doctype": "Lesson Booking",
				"learner": self.learner.name,
				"instructor": self.instructor.name,
				"vehicle": self.vehicle.name,
				"lesson_date": add_days(nowdate(), 1),
				"start_time": "09:00:00",
				"status": "Completed",
				"lesson_fee": 100,
			}
		).insert(ignore_permissions=True)

	def _feedback(self):
		return frappe.get_doc(
			{
				"doctype": "Learner Feedback",
				"learner": self.learner.name,
				"lesson": self.booking.name,
				"instructor": self.instructor.name,
				"rating": 5,
				"comments": "Great lesson",
			}
		).insert(ignore_permissions=True)

	def test_duplicate_feedback_blocked(self):
		self._feedback()
		with self.assertRaises(frappe.ValidationError):
			self._feedback()
