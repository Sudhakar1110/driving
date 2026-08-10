from __future__ import unicode_literals

import frappe

from driving_school.utils import is_logged_in_user_instructor

no_cache = 1


def get_context(context):
	context.no_cache = 1
	context.is_logged_in = frappe.session.user != "Guest"
	context.is_instructor = is_logged_in_user_instructor() if context.is_logged_in else False
	context.portal_page = "enquire"
	return context
