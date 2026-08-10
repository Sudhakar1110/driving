from __future__ import unicode_literals

import datetime

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, flt, get_first_day_of_week, getdate, now_datetime, today

from driving_school.utils import to_time


ACTIVE_BOOKING_STATUSES = ["Requested", "Confirmed", "On Waitlist"]


class LessonBooking(Document):
	def validate(self):
		self.set_duration_and_end_time()
		self.validate_lesson_date()
		self.validate_conflicts()
		self.validate_learner_status()
		self.validate_package()
		self.validate_schedule_rules()
		self.validate_instructor_leave()
		self.validate_vehicle_status()
		self.validate_instructor_category()
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

		for field in ("learner", "instructor", "vehicle"):
			existing = frappe.db.exists(
				"Lesson Booking",
				{
					field: self.get(field),
					"lesson_date": self.lesson_date,
					"start_time": self.start_time,
					"status": ["in", ACTIVE_BOOKING_STATUSES],
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

	def validate_schedule_rules(self):
		"""Enforce settings: max lessons per week and min gap between lessons.

		Only checked on create or when the schedule actually changes, so editing
		trivial fields on pre-existing bookings is never blocked retroactively.
		"""
		if self.status not in ACTIVE_BOOKING_STATUSES or not self.lesson_date:
			return
		if not self.is_new() and (
			self.lesson_date == self.get_db_value("lesson_date")
			and self.status == self.get_db_value("status")
		):
			return
		settings = frappe.get_single("Driving School Settings")

		max_per_week = cint(settings.max_lessons_per_week)
		if max_per_week:
			week_start = get_first_day_of_week(self.lesson_date)
			booked = frappe.db.count(
				"Lesson Booking",
				{
					"learner": self.learner,
					"lesson_date": ["between", [week_start, add_days(week_start, 6)]],
					"status": ["in", ACTIVE_BOOKING_STATUSES],
					"name": ["!=", self.name or ""],
				},
			)
			if booked >= max_per_week:
				frappe.throw(_("You can book a maximum of {0} lessons per week.").format(max_per_week))

		min_gap = cint(settings.min_gap_days_between_lessons)
		if min_gap:
			nearby = frappe.db.get_value(
				"Lesson Booking",
				{
					"learner": self.learner,
					"lesson_date": [
						"between",
						[add_days(self.lesson_date, -min_gap), add_days(self.lesson_date, min_gap)],
					],
					"status": ["in", ACTIVE_BOOKING_STATUSES],
					"name": ["!=", self.name or ""],
				},
				"name",
			)
			if nearby:
				frappe.throw(
					_("Lessons must be at least {0} day(s) apart. Booking {1} is too close to this date.").format(
						min_gap, nearby
					)
				)

	def validate_instructor_leave(self):
		"""Block booking with an instructor who is on approved leave."""
		if self.status not in ACTIVE_BOOKING_STATUSES or not (self.instructor and self.lesson_date):
			return
		if not self.is_new() and (
			self.instructor == self.get_db_value("instructor")
			and self.lesson_date == self.get_db_value("lesson_date")
		):
			return
		leave = frappe.db.get_value(
			"Instructor Leave",
			{
				"instructor": self.instructor,
				"status": "Approved",
				"from_date": ["<=", self.lesson_date],
				"to_date": [">=", self.lesson_date],
			},
			"name",
		)
		if leave:
			frappe.throw(
				_("Instructor {0} is on approved leave on {1} (Leave {2}).").format(
					self.instructor, self.lesson_date, leave
				)
			)

	def validate_vehicle_status(self):
		"""Only available, active vehicles can be booked (portal and desk)."""
		if self.status not in ACTIVE_BOOKING_STATUSES or not self.vehicle:
			return
		if not self.is_new() and self.vehicle == self.get_db_value("vehicle"):
			return
		vehicle = frappe.get_cached_doc("Driving Vehicle", self.vehicle)
		if not vehicle.is_active:
			frappe.throw(_("Vehicle {0} is inactive and cannot be booked.").format(self.vehicle))
		if vehicle.status != "Available":
			frappe.throw(
				_("Vehicle {0} is {1} and cannot be booked.").format(self.vehicle, vehicle.status)
			)

	def validate_instructor_category(self):
		"""Instructors with declared vehicle categories may only teach those categories."""
		if self.status not in ACTIVE_BOOKING_STATUSES or not (self.instructor and self.learner):
			return
		if not self.is_new() and self.instructor == self.get_db_value("instructor"):
			return
		categories = frappe.get_all(
			"Instructor Vehicle Category",
			filters={"parent": self.instructor},
			pluck="category",
		)
		if not categories:
			return  # instructor is not restricted
		learner = frappe.get_cached_doc("Learner", self.learner)
		category = self.category or learner.category
		if category and category not in categories:
			frappe.throw(
				_("Instructor {0} is not qualified to teach {1} lessons.").format(
					self.instructor, category
				)
			)

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
