from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today


class TheoryClass(Document):
	def validate(self):
		if self.class_date and getdate(self.class_date) < getdate(today()):
			frappe.throw(_("Class date cannot be in the past."))
		if self.start_time and self.end_time and self.end_time <= self.start_time:
			frappe.throw(_("End time must be after start time."))
