from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document


class DrivingSchoolBranch(Document):
	def validate(self):
		if not self.branch_name:
			frappe.throw(_("Branch name is required."))
