from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today


class DrivingTest(Document):
	def validate(self):
		if self.test_date and getdate(self.test_date) < getdate(today()):
			frappe.throw(_("Test date cannot be in the past."))
		if self.test_type == "Driving" and not self.instructor:
			frappe.msgprint(_("Please assign an instructor for a driving test."), indicator="orange")
		if self.result != "Pending" and self.score is None:
			frappe.msgprint(_("Please enter a score for the test result."), indicator="orange")

	def on_update(self):
		if self.result in ("Pass", "Fail"):
			old = self.get_db_value("result")
			if old != self.result:
				self.update_learner()

	def update_learner(self):
		learner = frappe.get_cached_doc("Learner", self.learner)

		if self.result == "Pass":
			if self.test_type == "Driving":
				if learner.status != "Passed":
					learner.status = "Passed"
					learner.save(ignore_permissions=True)
			else:
				if learner.training_stage == "Not Started":
					learner.training_stage = "Theory"
					learner.save(ignore_permissions=True)
		elif self.result == "Fail" and self.test_type == "Driving":
			# "Test Ready" is recorded on training_stage when a package is
			# completed (lesson_booking.handle_completion); send the learner
			# back to practical training after a failed driving test.
			if learner.training_stage == "Test Ready":
				learner.training_stage = "Practical"
				learner.save(ignore_permissions=True)
