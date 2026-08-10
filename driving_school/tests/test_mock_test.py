from __future__ import unicode_literals

import frappe
from frappe.tests import IntegrationTestCase

from driving_school.api import get_mock_questions, submit_mock_test
from driving_school.tests.helpers import make_learner


def make_question(category="Car"):
	return frappe.get_doc(
		{
			"doctype": "Mock Test Question",
			"question": "Test question " + frappe.generate_hash("", 4),
			"category": category,
			"topic": "Test",
			"option_a": "Option A",
			"option_b": "Option B",
			"option_c": "Option C",
			"option_d": "Option D",
			"correct_answer": "B",
			"is_active": 1,
		}
	).insert(ignore_permissions=True)


class TestMockTest(IntegrationTestCase):
	def setUp(self):
		self.learner = make_learner("Mock Test Learner")

	def test_questions_do_not_expose_answer(self):
		make_question()
		result = get_mock_questions("Car", 1)
		self.assertEqual(len(result), 1)
		self.assertNotIn("correct_answer", result[0])

	def test_questions_respect_count(self):
		for _ in range(3):
			make_question()
		self.assertEqual(len(get_mock_questions("Car", 2)), 2)

	def test_scoring_pass_and_fail(self):
		q1 = make_question()  # correct answer B
		q2 = make_question()
		result = submit_mock_test(
			"Car",
			[
				{"question": q1.name, "selected_answer": "B"},
				{"question": q2.name, "selected_answer": "A"},
			],
		)
		self.assertEqual(result["total_questions"], 2)
		self.assertEqual(result["correct_answers"], 1)
		self.assertEqual(result["score_percent"], 50)
		self.assertEqual(result["result"], "Fail")
		# per-answer review is returned
		self.assertEqual(len(result["answers"]), 2)
		self.assertEqual(result["answers"][0]["correct_answer"], "B")

	def test_full_marks_passes(self):
		q1 = make_question()
		result = submit_mock_test("Car", [{"question": q1.name, "selected_answer": "B"}])
		self.assertEqual(result["result"], "Pass")
		self.assertEqual(result["score_percent"], 100)
