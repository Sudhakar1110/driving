from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document


class DrivingInstructor(Document):
	def validate(self):
		self.validate_license()

	def validate_license(self):
		if not self.license_number:
			return
		existing = frappe.db.get_value(
			"Driving Instructor",
			{"license_number": self.license_number, "name": ["!=", self.name]},
			"name",
		)
		if existing:
			frappe.throw(
				_("License number {0} is already registered to instructor {1}").format(
					self.license_number, existing
				)
			)
