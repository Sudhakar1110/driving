from __future__ import unicode_literals

import datetime

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate, now_datetime, to_time, today


class LessonBooking(Document):
	def validate(self):
		self.set_duration_and_end_time()
		self.validate_lesson_date()
		self.validate_conflicts()
		self.validate_learner_status()
		self.validate_package()
		self.validate_status_transition()
		self.apply_cancellation_fee()

	def set_duration_and_end_time(self):
		if not self.duration_minutes:
			settings = frappe.get_single("Driving School Settings")
			self.duration_minutes = cint(settings.lesson_duration_minutes) or 60
		if self.start_time and self.duration_minutes:
			base = datetime.datetime.combine(datetime.date(2000, 1, 1), to_time(self.start_time))
			self.end_time = (
				base + datetime.timedelta(minutes=cint(self.duration_minutes))
			).time()

	def validate_lesson_date(self):
		if not self.start_time:
			frappe.throw(_("Start time is required."))
		if self.lesson_date and getdate(self.lesson_date) < getdate(today()):
			frappe.throw(_("Lesson date cannot be in the past."))
		if self.lesson_date and getdate(self.lesson_date) == getdate(today()):
			start_dt = datetime.datetime.combine(getdate(self.lesson_date), to_time(self.start_time))
			if start_dt <= datetime.datetime.now():
				frappe.throw(_("Lesson start time cannot be in the past."))

	def validate_conflicts(self):
		"""No double-booking for the learner, instructor or vehicle."""
		if not (self.learner and self.instructor and self.vehicle and self.lesson_date and self.start_time):
			return

		active_statuses = ["Requested", "Confirmed", "On Waitlist"]
		for field in ("learner", "instructor", "vehicle"):
			existing = frappe.db.exists(
				"Lesson Booking",
				{
					field: self.get(field),
					"lesson_date": self.lesson_date,
					"start_time": self.start_time,
					"status": ["in", active_statuses],
					"name": ["!=", self.name or ""],
				},
			)
			if existing:
				frappe.throw(
					_("The {0} already has a lesson on {1} at {2} (Booking {3}).").format(
						field.replace("_", " "), self.lesson_date, self.start_time, existing
					)
				)

	def validate_learner_status(self):
		learner = frappe.get_cached_doc("Learner", self.learner)
		if learner.status in ("Enquired", "Dropped"):
			frappe.throw(_("Learner status is {0}. Lessons cannot be booked.").format(learner.status))

	def validate_package(self):
		if self.package:
			pkg = frappe.get_cached_doc("Learner Package", self.package)
			if not pkg.is_active:
				frappe.throw(_("Package {0} is inactive.").format(self.package))
			if pkg.expiry_date and getdate(pkg.expiry_date) < getdate(self.lesson_date):
				frappe.throw(_("Package {0} expired on {1}.").format(self.package, pkg.expiry_date))
			if cint(pkg.lessons_used) >= cint(pkg.lessons_count):
				frappe.throw(_("Package {0} has no lessons remaining.").format(self.package))
			if flt(pkg.balance_amount) > 0:
				frappe.throw(
					_("Package {0} has an outstanding balance of {1}. Clear it before booking.").format(
						self.package, flt(pkg.balance_amount)
					)
				)
			if not self.lesson_fee:
				self.lesson_fee = 0
		else:
			if not self.lesson_fee:
				frappe.throw(_("Please select a Learner Package or enter a Lesson Fee."))

	def validate_status_transition(self):
		if self.is_new():
			return
		old = self.get_db_value("status")
		if old == "Completed" and self.status != "Completed":
			frappe.throw(_("Completed bookings cannot be reopened."))

	def apply_cancellation_fee(self):
		if self.status != "Cancelled":
			return
		if not self.is_new() and self.get_db_value("status") == "Cancelled":
			return

		settings = frappe.get_single("Driving School Settings")
		if not (settings.cancellation_notice_hours and settings.cancellation_fee_percent):
			self.cancellation_fee = 0
			return

		start_dt = datetime.datetime.combine(
			getdate(self.lesson_date), to_time(self.start_time) if self.start_time else datetime.time(0, 0)
		)
		hours_left = (start_dt - now_datetime()).total_seconds() / 3600
		if hours_left < cint(settings.cancellation_notice_hours):
			self.cancellation_fee = flt(self.lesson_fee) * flt(settings.cancellation_fee_percent) / 100
		else:
			self.cancellation_fee = 0

	def on_update(self):
		self.handle_completion()

	def handle_completion(self):
		"""Consume a package lesson when a booked lesson is completed."""
		if self.status == "Completed" and self.package and not self.package_lesson_counted:
			pkg = frappe.get_cached_doc("Learner Package", self.package)
			pkg.lessons_used = cint(pkg.lessons_used) + 1
			pkg.save(ignore_permissions=True)
			frappe.db.set_value("Lesson Booking", self.name, "package_lesson_counted", 1)

			learner = frappe.get_cached_doc("Learner", self.learner)
			if cint(pkg.lessons_used) >= cint(pkg.lessons_count):
				if learner.training_stage != "Test Ready":
					learner.training_stage = "Test Ready"
					learner.save(ignore_permissions=True)
