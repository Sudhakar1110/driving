from __future__ import unicode_literals

import frappe

no_cache = 1


def get_context(context):
	context.no_cache = 1
	return context
