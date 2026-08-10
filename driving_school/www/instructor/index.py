from __future__ import unicode_literals

import frappe

from driving_school.utils import get_instructor_for_user

no_cache = 1


def get_context(context):
	context.no_cache = 1
	user = frappe.session.user
	context.instructor = None
	context.is_guest = user == "Guest"
	context.is_logged_in = user != "Guest"
	context.is_instructor = False
	context.portal_page = "instructor"
	if user and user != "Guest":
		context.instructor = get_instructor_for_user(user)
		context.is_instructor = context.instructor is not None
	return context
