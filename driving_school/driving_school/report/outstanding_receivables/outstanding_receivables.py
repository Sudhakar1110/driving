from __future__ import unicode_literals

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})

	columns = [
		{"label": _("Learner"), "fieldname": "learner", "fieldtype": "Link", "options": "Learner", "width": 130},
		{"label": _("Learner Name"), "fieldname": "learner_name", "fieldtype": "Data", "width": 180},
		{"label": _("Mobile"), "fieldname": "mobile_number", "fieldtype": "Data", "width": 120},
		{"label": _("Package"), "fieldname": "package_name", "fieldtype": "Data", "width": 160},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 110},
		{"label": _("Paid"), "fieldname": "paid_amount", "fieldtype": "Currency", "width": 110},
		{"label": _("Balance"), "fieldname": "balance_amount", "fieldtype": "Currency", "width": 110},
		{"label": _("Expiry Date"), "fieldname": "expiry_date", "fieldtype": "Date", "width": 110},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
	]

	conditions = "p.balance_amount > 0 and ifnull(p.learner, '') != ''"
	params = {}

	if filters.get("branch"):
		conditions += " and l.branch = %(branch)s"
		params["branch"] = filters.get("branch")

	data = frappe.db.sql(
		"""
		select l.name as learner, l.learner_name, l.mobile_number,
			p.package_name, p.discounted_amount as amount,
			p.paid_amount, p.balance_amount, p.expiry_date, p.status
		from `tabLearner Package` p
		left join `tabLearner` l on l.name = p.learner
		where {conditions}
		order by p.balance_amount desc
		""".format(conditions=conditions),
		params,
		as_dict=1,
	)

	report_summary = [
		{
			"label": _("Total Outstanding"),
			"value": sum(row["balance_amount"] or 0 for row in data),
			"datatype": "Currency",
			"indicator": "red",
		},
		{"label": _("Learners with Balance"), "value": len(data), "datatype": "Int", "indicator": "blue"},
	]

	return columns, data, None, None, report_summary
