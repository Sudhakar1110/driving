from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document


class MockTestQuestion(Document):
	def validate(self):
		options = [self.option_a, self.option_b, self.option_c, self.option_d]
		blank = [i + 1 for i, o in enumerate(options) if not o]
		if blank:
			frappe.throw(
				_("Options {0} cannot be empty.").format(", ".join(str(b) for b in blank))
			)
		if not self.correct_answer:
			frappe.throw(_("Please select the correct answer."))
