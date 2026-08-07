from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt


class MockTestAttempt(Document):
	def validate(self):
		self.compute_score()

	def compute_score(self):
		if not self.get("answers"):
			return

		correct = 0
		total_marks = 0
		obtained_marks = 0

		for answer in self.answers:
			question = frappe.get_cached_doc("Mock Test Question", answer.question)
			answer.question_text = question.question
			answer.correct_answer = question.correct_answer
			answer.marks = cint(question.marks) or 1
			answer.is_correct = 1 if answer.selected_answer == question.correct_answer else 0

			total_marks += answer.marks
			if answer.is_correct:
				correct += 1
				obtained_marks += answer.marks

		self.total_questions = len(self.answers)
		self.correct_answers = correct
		self.score_percent = flt(obtained_marks * 100.0 / total_marks, 1) if total_marks else 0

		pass_percent = cint(self.pass_percentage) or 60
		self.result = "Pass" if self.score_percent >= pass_percent else "Fail"
