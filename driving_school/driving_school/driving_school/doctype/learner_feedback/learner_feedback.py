from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document


class LearnerFeedback(Document):
	def validate(self):
		self.validate_lesson_ownership()
		self.validate_duplicate()

	def validate_lesson_ownership(self):
		if not self.lesson:
			return
		lesson_learner = frappe.db.get_value("Lesson Booking", self.lesson, "learner")
		if lesson_learner != self.learner:
			frappe.throw(_("Feedback can only be given for the learner's own lesson bookings."))

	def validate_duplicate(self):
		if not self.lesson:
			return
		existing = frappe.db.exists(
			"Learner Feedback",
			{
				"lesson": self.lesson,
				"name": ["!=", self.name or ""],
			},
		)
		if existing:
			frappe.throw(_("Feedback already submitted for this lesson ({0}).").format(existing))
