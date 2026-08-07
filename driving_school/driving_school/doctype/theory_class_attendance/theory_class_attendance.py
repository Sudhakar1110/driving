from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document


class TheoryClassAttendance(Document):
	def validate(self):
		self.validate_duplicate()

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
