from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class LearnerPayment(Document):
	def validate(self):
		if self.payment_type == "Refund":
			# refunds may be entered as negative amounts; excluded from paid totals
			return
		if flt(self.amount) <= 0:
			frappe.throw(_("Payment amount must be greater than zero."))

	def on_update(self):
		self.refresh_package_balance()

	def refresh_package_balance(self):
		"""Recompute the linked package's paid amount and balance."""
		if not self.package:
			return
		pkg = frappe.get_doc("Learner Package", self.package)
		pkg.save(ignore_permissions=True)
