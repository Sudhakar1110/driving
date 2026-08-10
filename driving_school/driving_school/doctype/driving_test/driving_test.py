from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, getdate, today


class DrivingTest(Document):
	def validate(self):
		if self.test_date and getdate(self.test_date) < getdate(today()):
			frappe.throw(_("Test date cannot be in the past."))
		if self.test_type == "Driving" and not self.instructor:
			frappe.msgprint(_("Please assign an instructor for a driving test."), indicator="orange")
		if self.result != "Pending" and self.score is None:
			frappe.msgprint(_("Please enter a score for the test result."), indicator="orange")
		self.validate_test_attempts()

	def validate_test_attempts(self):
		"""Learners may not exceed the test attempts included in their active packages."""
		if not self.learner:
			return
		allowed = frappe.db.sql(
			"""
			select ifnull(sum(test_attempts_included), 0) from `tabLearner Package`
			where learner = %(learner)s and status = 'Active'
			""",
			{"learner": self.learner},
		)[0][0]
		if not cint(allowed):
			return
		used = frappe.db.count(
			"Driving Test",
			{
				"learner": self.learner,
				"test_type": "Driving",
				"name": ["!=", self.name or ""],
			},
		)
		if used >= cint(allowed):
			frappe.throw(
				_("Learner has used all {0} test attempts included in their package.").format(
					cint(allowed)
				)
			)

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

			# Mark the learner Failed once the package's test attempts run out.
			allowed = frappe.db.sql(
				"""
				select ifnull(sum(test_attempts_included), 0) from `tabLearner Package`
				where learner = %(learner)s and status = 'Active'
				""",
				{"learner": learner.name},
			)[0][0]
			used = frappe.db.count(
				"Driving Test", {"learner": learner.name, "test_type": "Driving"}
			)
			if cint(allowed) and used >= cint(allowed) and learner.status != "Failed":
				learner.status = "Failed"
				learner.save(ignore_permissions=True)
