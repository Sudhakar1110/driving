from __future__ import unicode_literals

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from driving_school.api import book_lesson
from driving_school.tests.helpers import (
	make_instructor,
	make_learner,
	make_package,
	make_vehicle,
	set_limits,
)


class TestLessonBookingRules(IntegrationTestCase):
	def setUp(self):
		self.learner = make_learner("Booking Test Learner")
		self.instructor = make_instructor(["Car"])
		self.vehicle = make_vehicle()
		self.package = make_package(self.learner)

	def _book(self, day, time="09:00:00"):
		return book_lesson(
			day, time, self.instructor.name, self.vehicle.name, package=self.package.name
		)

	def test_weekly_limit_enforced(self):
		set_limits(max_per_week=2, min_gap=0)
		day = add_days(nowdate(), 2)
		self._book(day, "09:00:00")
		self._book(day, "10:00:00")
		with self.assertRaises(frappe.ValidationError):
			self._book(day, "11:00:00")

	def test_min_gap_between_lessons_enforced(self):
		set_limits(max_per_week=10, min_gap=1)
		day = add_days(nowdate(), 2)
		self._book(day, "09:00:00")
		# consecutive day is too close
		with self.assertRaises(frappe.ValidationError):
			self._book(add_days(day, 1), "09:00:00")
		# two days later is fine
		self._book(add_days(day, 2), "09:00:00")

	def test_instructor_on_leave_blocked(self):
		set_limits(max_per_week=10, min_gap=0)
		day = add_days(nowdate(), 5)
		frappe.get_doc(
			{
				"doctype": "Instructor Leave",
				"instructor": self.instructor.name,
				"from_date": day,
				"to_date": day,
				"status": "Approved",
			}
		).insert(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			self._book(day)

	def test_instructor_on_pending_leave_allowed(self):
		set_limits(max_per_week=10, min_gap=0)
		day = add_days(nowdate(), 5)
		frappe.get_doc(
			{
				"doctype": "Instructor Leave",
				"instructor": self.instructor.name,
				"from_date": day,
				"to_date": day,
				"status": "Requested",
			}
		).insert(ignore_permissions=True)
		self._book(day)

	def test_vehicle_status_enforced(self):
		set_limits(max_per_week=10, min_gap=0)
		frappe.db.set_value("Driving Vehicle", self.vehicle.name, "status", "Maintenance")
		with self.assertRaises(frappe.ValidationError):
			self._book(add_days(nowdate(), 3))

	def test_instructor_category_enforced(self):
		set_limits(max_per_week=10, min_gap=0)
		moto_learner = make_learner("Moto Learner", category="Motorcycle")
		doc = frappe.get_doc(
			{
				"doctype": "Lesson Booking",
				"learner": moto_learner.name,
				"instructor": self.instructor.name,
				"vehicle": self.vehicle.name,
				"lesson_date": add_days(nowdate(), 3),
				"start_time": "09:00:00",
				"status": "Confirmed",
				"lesson_fee": 100,
			}
		)
		with self.assertRaises(frappe.ValidationError):
			doc.insert(ignore_permissions=True)

	def test_unrestricted_instructor_allowed(self):
		set_limits(max_per_week=10, min_gap=0)
		general = make_instructor()  # no categories declared
		frappe.get_doc(
			{
				"doctype": "Lesson Booking",
				"learner": self.learner.name,
				"instructor": general.name,
				"vehicle": self.vehicle.name,
				"lesson_date": add_days(nowdate(), 3),
				"start_time": "09:00:00",
				"status": "Confirmed",
				"lesson_fee": 100,
			}
		).insert(ignore_permissions=True)
