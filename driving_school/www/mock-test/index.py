from __future__ import unicode_literals

import frappe

from driving_school.utils import get_learner_for_user

no_cache = 1


def get_context(context):
	context.no_cache = 1
	context.learner = None

	if frappe.session.user == "Guest":
		return context

	name = get_learner_for_user()
	if not name:
		return context

	context.learner = name
	context.learner_name = frappe.db.get_value("Learner", name, "learner_name")
	return context
