from __future__ import unicode_literals

import frappe

from driving_school.utils import get_learner_for_user, is_logged_in_user_instructor

no_cache = 1


def get_context(context):
	context.no_cache = 1
	user = frappe.session.user
	context.is_logged_in = user != "Guest"
	context.is_instructor = is_logged_in_user_instructor() if context.is_logged_in else False
	context.portal_page = "schedules"

	# Learners see their name so they can jump straight to booking. This page is
	# read-only public info - it never auto-creates records, only resolves one
	# if the user already has a profile.
	context.learner = None
	if context.is_logged_in:
		name = get_learner_for_user(user)
		if name:
			context.learner = frappe.db.get_value("Learner", name, "learner_name")
	return context
