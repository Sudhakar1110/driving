from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document


class Enquiry(Document):
	def validate(self):
		self.validate_mobile_number()

	def validate_mobile_number(self):
		if not self.mobile_number:
			frappe.throw(_("Mobile number is required."))

	@frappe.whitelist()
	def convert_to_learner(self):
		"""Convert this enquiry into a registered Learner."""
		if self.status == "Registered":
			frappe.throw(_("This enquiry is already converted to a learner."))

		learner = frappe.get_doc(
			{
				"doctype": "Learner",
				"learner_name": self.lead_name,
				"mobile_number": self.mobile_number,
				"email": self.email or "",
				"category": self.category_of_interest,
				"source": self.source,
				"branch": self.branch,
				"status": "Registered",
				"lead": self.name,
			}
		)
		learner.insert(ignore_permissions=True)

		self.db_set("status", "Registered")
		self.db_set("learner", learner.name)
		return learner.name
