from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class InstructorLeave(Document):
	def validate(self):
		self.validate_dates()
		self.validate_overlap()

	def validate_dates(self):
		if self.from_date and self.to_date and getdate(self.to_date) < getdate(self.from_date):
			frappe.throw(_("To Date cannot be before From Date."))

	def validate_overlap(self):
		if not (self.instructor and self.from_date and self.to_date):
			return
		overlap = frappe.db.sql(
			"""
			select name from `tabInstructor Leave`
			where instructor = %(instructor)s
				and status in ("Requested", "Approved")
				and name != %(name)s
				and %(from)s <= to_date and %(to)s >= from_date
			""",
			{
				"instructor": self.instructor,
				"name": self.name or "",
				"from": self.from_date,
				"to": self.to_date,
			},
		)
		if overlap:
			frappe.throw(
				_("Instructor already has leave overlapping these dates ({0}).").format(overlap[0][0])
			)
