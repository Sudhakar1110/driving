from __future__ import unicode_literals

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})

	columns = [
		{"label": _("Vehicle"), "fieldname": "vehicle", "fieldtype": "Link", "options": "Driving Vehicle", "width": 130},
		{"label": _("Vehicle Number"), "fieldname": "vehicle_number", "fieldtype": "Data", "width": 140},
		{"label": _("Model"), "fieldname": "vehicle_model", "fieldtype": "Data", "width": 140},
		{"label": _("Type"), "fieldname": "vehicle_type", "fieldtype": "Data", "width": 110},
		{"label": _("Lessons"), "fieldname": "lessons", "fieldtype": "Int", "width": 90},
		{"label": _("Hours Used"), "fieldname": "hours_used", "fieldtype": "Float", "width": 100, "precision": 1},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
	]

	conditions = "1=1"
	params = {}
	if filters.get("from_date"):
		conditions += " and lb.lesson_date >= %(from_date)s"
		params["from_date"] = filters.get("from_date")
	if filters.get("to_date"):
		conditions += " and lb.lesson_date <= %(to_date)s"
		params["to_date"] = filters.get("to_date")

	data = frappe.db.sql(
		"""
		select v.name as vehicle, v.vehicle_number, v.vehicle_model, v.vehicle_type,
			count(lb.name) as lessons,
			coalesce(sum(coalesce(lb.duration_minutes, 60)) / 60.0, 0) as hours_used,
			v.status
		from `tabDriving Vehicle` v
		left join `tabLesson Booking` lb on lb.vehicle = v.name and lb.status = 'Completed' and {conditions}
		group by v.name
		order by lessons desc
		""".format(conditions=conditions),
		params,
		as_dict=1,
	)

	for row in data:
		row["lessons"] = row["lessons"] or 0
		row["hours_used"] = round(row["hours_used"] or 0, 1)

	report_summary = [
		{
			"label": _("Total Completed Lessons"),
			"value": sum(row["lessons"] or 0 for row in data),
			"datatype": "Int",
			"indicator": "green",
		},
		{
			"label": _("Total Hours"),
			"value": sum(row["hours_used"] or 0 for row in data),
			"datatype": "Float",
			"indicator": "blue",
		},
	]

	return columns, data, None, None, report_summary
