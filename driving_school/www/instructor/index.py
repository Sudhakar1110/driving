from __future__ import unicode_literals

import frappe

from driving_school.utils import get_instructor_for_user

no_cache = 1


def get_context(context):
	context.no_cache = 1
	user = frappe.session.user
	context.instructor = None
	context.is_guest = user == "Guest"
	if user and user != "Guest":
		context.instructor = get_instructor_for_user(user)
	return context
