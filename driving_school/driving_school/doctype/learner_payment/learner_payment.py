from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate

from driving_school.utils import erpnext_installed


def _first_non_group(doctype, field="name"):
	"""First non-group record of a doctype (for ERPNext defaults)."""
	return frappe.db.get_value(doctype, {"is_group": 0}, field, order_by="creation asc")


def _default_company():
	company = frappe.db.get_single_value("Global Defaults", "default_company")
	if not company:
		company = frappe.get_all("Company", limit=1, pluck="name")
	return company[0] if company else None


def _get_or_create_customer(learner, learner_id):
	customer_name = "Learner - {0} ({1})".format(learner.learner_name, learner_id)
	existing = frappe.db.get_value("Customer", {"customer_name": customer_name}, "name")
	if existing:
		return existing

	customer_group = _first_non_group("Customer Group") or "Commercial"
	territory = (
		frappe.db.get_value("Territory", "All Territories", "name")
		or _first_non_group("Territory")
		or "All Territories"
	)
	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": customer_name,
			"customer_group": customer_group,
			"territory": territory,
			"customer_type": "Individual",
		}
	)
	customer.insert(ignore_permissions=True)
	return customer.name


def _get_or_create_service_item():
	item_code = "DRV-SRV"
	if frappe.db.exists("Item", item_code):
		return item_code

	item_group = _first_non_group("Item Group") or "Services"
	item = frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": item_code,
			"item_name": "Driving School Service",
			"item_group": item_group,
			"stock_uom": "Nos",
			"is_stock_item": 0,
			"is_sales_item": 1,
			"disabled": 0,
		}
	)
	item.insert(ignore_permissions=True)
	return item.name


class LearnerPayment(Document):
	def validate(self):
		if self.payment_type == "Refund":
			# refunds may be entered as negative amounts; excluded from paid totals
			return
		if flt(self.amount) <= 0:
			frappe.throw(_("Payment amount must be greater than zero."))

	def on_update(self):
		self.create_sales_invoice()
		self.refresh_package_balance()

	def create_sales_invoice(self):
		"""Auto-create an ERPNext Sales Invoice when a payment is received.

		Runs only on ERPNext sites. Failures are logged and never block the
		payment; if posting (submit) fails, the invoice is kept as a draft so
		the reference is still captured.
		"""
		if self.sales_invoice_ref:
			return
		if self.payment_type == "Refund":
			return
		if self.status not in ("Received", "Reconciled"):
			return
		if not erpnext_installed():
			return

		try:
			company = _default_company()
			if not company:
				return

			# Resolve defaults from the Company so submit usually succeeds on a
			# configured site; on an unconfigured site the draft is still kept.
			income_account = frappe.db.get_value("Company", company, "default_income_account")
			debit_to = frappe.db.get_value("Company", company, "default_receivable_account")
			cost_center = frappe.db.get_value("Company", company, "cost_center")

			customer = None
			if self.learner:
				learner = frappe.get_cached_doc("Learner", self.learner)
				customer = _get_or_create_customer(learner, self.learner)
			if not customer:
				customer = frappe.db.get_value("Customer", {}, "name")
			if not customer:
				return

			item = _get_or_create_service_item()
			posting_date = self.payment_date or nowdate()

			invoice = frappe.get_doc(
				{
					"doctype": "Sales Invoice",
					"customer": customer,
					"company": company,
					"posting_date": posting_date,
					"due_date": posting_date,
					"update_stock": 0,
					"debit_to": debit_to,
					"cost_center": cost_center,
					"items": [
						{
							"item_code": item,
							"qty": 1,
							"rate": flt(self.amount),
							"amount": flt(self.amount),
							"income_account": income_account,
							"cost_center": cost_center,
						}
					],
					"remarks": "Auto-created from Learner Payment {0}".format(self.name),
				}
			)
			invoice.insert(ignore_permissions=True)
			self.db_set("sales_invoice_ref", invoice.name)
			try:
				invoice.submit()
			except Exception:
				frappe.log_error(
					frappe.get_traceback(),
					"Driving School: sales invoice submit failed (kept as draft)",
				)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Driving School: sales invoice creation failed")

	def refresh_package_balance(self):
		"""Recompute the linked package's paid amount and balance."""
		if not self.package:
			return
		pkg = frappe.get_doc("Learner Package", self.package)
		pkg.save(ignore_permissions=True)
