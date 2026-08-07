from __future__ import unicode_literals

import frappe

from driving_school.utils import get_learner_for_context

no_cache = 1


def get_context(context):
	context.no_cache = 1
	context.learner, context.learner_name = get_learner_for_context()
	return context
