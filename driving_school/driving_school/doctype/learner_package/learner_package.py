from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, flt, getdate, today


class LearnerPackage(Document):
	def validate(self):
		self.set_status_and_dates()
		self.validate_amounts()
		self.update_paid_amount()

	def set_status_and_dates(self):
		if not self.status:
			self.status = "Active"

		if self.validity_days and not self.expiry_date:
			self.expiry_date = add_days(today(), cint(self.validity_days))

		if self.expiry_date and getdate(self.expiry_date) < getdate(today()):
			if self.status == "Active":
				self.status = "Expired"

	def validate_amounts(self):
		if cint(self.lessons_count) <= 0:
			frappe.throw(_("Lessons included must be greater than zero."))

		# Friendly guard instead of a raw DB error: the amount columns are
		# DECIMAL(18,2) - at most 16 integer digits - so values of 1e16 and
		# above overflow on insert ("Out of range value for column 'amount'").
		# (Boundary is >= 1e16: 9999999999999999.99 fits, 10000000000000000
		# does not. Using an int literal avoids float rounding at the limit.)
		MAX_AMOUNT = 10000000000000000
		for label, value in (
			(_("Amount"), self.amount),
			(_("Discount Amount"), self.discount_amount),
		):
			if flt(value) < 0:
				frappe.throw(_("{0} cannot be negative.").format(label))
			if flt(value) >= MAX_AMOUNT:
				frappe.throw(
					_("{0} is too large ({1}). Please enter a valid package price.").format(
						label, flt(value)
					)
				)

		self.discounted_amount = flt(self.amount) - flt(self.discount_amount)
		if self.discounted_amount < 0:
			frappe.throw(_("Discount amount cannot exceed the package amount."))

	def update_paid_amount(self):
		paid = frappe.db.sql(
			"""
			select ifnull(sum(amount), 0) from `tabLearner Payment`
			where package = %(package)s
				and docstatus < 2
				and status in ("Received", "Reconciled")
				and payment_type != "Refund"
			""",
			{"package": self.name},
		)[0][0]

		self.paid_amount = flt(paid)
		self.balance_amount = flt(self.discounted_amount) - flt(paid)

		if cint(self.lessons_used) >= cint(self.lessons_count) and self.balance_amount <= 0:
			if self.status == "Active":
				self.status = "Completed"
