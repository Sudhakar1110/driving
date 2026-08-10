from __future__ import unicode_literals

import datetime

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from driving_school.utils import to_time


def class_duration_hours(cls):
	"""Duration of a theory class in hours (defaults to 1 hour)."""
	if cls.start_time and cls.end_time:
		start = to_time(cls.start_time)
		end = to_time(cls.end_time)
		if end > start:
			base = datetime.date(2000, 1, 1)
			seconds = (
				datetime.datetime.combine(base, end) - datetime.datetime.combine(base, start)
			).total_seconds()
			return max(flt(seconds / 3600.0), 0.25)
	return 1.0


class TheoryClassAttendance(Document):
	def validate(self):
		self.validate_duplicate()
		self.validate_theory_hours()

	def validate_duplicate(self):
		if not (self.theory_class and self.learner):
			return
		existing = frappe.db.exists(
			"Theory Class Attendance",
			{
				"theory_class": self.theory_class,
				"learner": self.learner,
				"name": ["!=", self.name or ""],
			},
		)
		if existing:
			frappe.throw(
				_("Attendance already recorded for this learner in this class ({0}).").format(
					existing
				)
			)

	def validate_theory_hours(self):
		"""Learners may not exceed the theory hours included in their active packages."""
		if not (self.learner and self.theory_class) or self.status != "Present":
			return

		allowed = frappe.db.sql(
			"""
			select ifnull(sum(theory_class_hours), 0) from `tabLearner Package`
			where learner = %(learner)s and status = 'Active'
			""",
			{"learner": self.learner},
		)[0][0]
		if not cint(allowed):
			return

		total = class_duration_hours(frappe.get_cached_doc("Theory Class", self.theory_class))
		attended = frappe.get_all(
			"Theory Class Attendance",
			filters={
				"learner": self.learner,
				"status": "Present",
				"name": ["!=", self.name or ""],
			},
			fields=["theory_class"],
		)
		for row in attended:
			total += class_duration_hours(frappe.get_cached_doc("Theory Class", row.theory_class))

		if total > flt(allowed):
			frappe.throw(
				_("Learner has used all {0} theory hours included in their package.").format(
					cint(allowed)
				)
			)
