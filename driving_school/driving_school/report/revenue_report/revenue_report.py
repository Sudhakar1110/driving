from __future__ import unicode_literals

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})

	columns = [
		{"label": _("Payment Date"), "fieldname": "payment_date", "fieldtype": "Date", "width": 110},
		{"label": _("Learner"), "fieldname": "learner", "fieldtype": "Link", "options": "Learner", "width": 130},
		{"label": _("Learner Name"), "fieldname": "learner_name", "fieldtype": "Data", "width": 180},
		{"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Driving School Branch", "width": 130},
		{"label": _("Package"), "fieldname": "package", "fieldtype": "Link", "options": "Learner Package", "width": 130},
		{"label": _("Type"), "fieldname": "payment_type", "fieldtype": "Data", "width": 120},
		{"label": _("Mode"), "fieldname": "mode_of_payment", "fieldtype": "Data", "width": 120},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 110},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
	]

	conditions = "1=1"
	params = {}

	if filters.get("from_date"):
		conditions += " and lp.payment_date >= %(from_date)s"
		params["from_date"] = filters.get("from_date")
	if filters.get("to_date"):
		conditions += " and lp.payment_date <= %(to_date)s"
		params["to_date"] = filters.get("to_date")
	if filters.get("payment_type"):
		conditions += " and lp.payment_type = %(payment_type)s"
		params["payment_type"] = filters.get("payment_type")
	if filters.get("status"):
		conditions += " and lp.status = %(status)s"
		params["status"] = filters.get("status")
	if filters.get("branch"):
		conditions += " and l.branch = %(branch)s"
		params["branch"] = filters.get("branch")

	data = frappe.db.sql(
		"""
		select lp.payment_date, lp.learner, lp.learner_name, l.branch, lp.package,
			lp.payment_type, lp.mode_of_payment, lp.amount, lp.status
		from `tabLearner Payment` lp
		left join `tabLearner` l on l.name = lp.learner
		where {conditions}
		order by lp.payment_date desc, lp.creation desc
		""".format(conditions=conditions),
		params,
		as_dict=1,
	)

	chart = None
	if data:
		by_date = {}
		for row in data:
			if row.status in ("Received", "Reconciled"):
				key = str(row.payment_date)
				by_date[key] = by_date.get(key, 0) + (row.amount or 0)
		labels = sorted(by_date.keys())
		chart = {
			"data": {
				"labels": labels,
				"datasets": [{"name": _("Amount Received"), "values": [by_date[d] for d in labels]}],
			},
			"type": "bar",
		}

	report_summary = []
	total_received = sum(
		row["amount"] or 0 for row in data if row["status"] in ("Received", "Reconciled")
	)
	report_summary.append(
		{"label": _("Total Received"), "value": total_received, "datatype": "Currency", "indicator": "green"}
	)
	report_summary.append(
		{"label": _("Payment Entries"), "value": len(data), "datatype": "Int", "indicator": "blue"}
	)

	return columns, data, None, chart, report_summary
