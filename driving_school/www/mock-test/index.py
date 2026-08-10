from __future__ import unicode_literals

import frappe

from driving_school.utils import get_learner_for_context

no_cache = 1


def get_context(context):
	context.no_cache = 1
	context.learner, context.learner_name = get_learner_for_context()
	context.pass_percentage = frappe.get_single("Driving School Settings").mock_test_pass_percentage or 60
	return context
