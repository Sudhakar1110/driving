from __future__ import unicode_literals

import frappe

from driving_school.utils import get_learner_for_context, is_logged_in_user_instructor

no_cache = 1


def get_context(context):
	context.no_cache = 1
	context.learner, context.learner_name = get_learner_for_context()
	context.is_logged_in = frappe.session.user != "Guest"
	context.is_instructor = is_logged_in_user_instructor() if context.is_logged_in else False
	context.portal_page = "portal-home"
	return context
