from __future__ import unicode_literals

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})

	columns = [
		{"label": _("Instructor"), "fieldname": "instructor", "fieldtype": "Link", "options": "Driving Instructor", "width": 130},
		{"label": _("Instructor Name"), "fieldname": "instructor_name", "fieldtype": "Data", "width": 180},
		{"label": _("Total Lessons"), "fieldname": "total_lessons", "fieldtype": "Int", "width": 110},
		{"label": _("Completed"), "fieldname": "completed", "fieldtype": "Int", "width": 100},
		{"label": _("No Shows"), "fieldname": "no_shows", "fieldtype": "Int", "width": 90},
		{"label": _("Tests Passed"), "fieldname": "tests_passed", "fieldtype": "Int", "width": 110},
		{"label": _("Avg Rating"), "fieldname": "avg_rating", "fieldtype": "Float", "width": 100, "precision": 1},
	]

	conditions = "1=1"
	params = {}
	if filters.get("from_date"):
		conditions += " and lbx.lesson_date >= %(from_date)s"
		params["from_date"] = filters.get("from_date")
	if filters.get("to_date"):
		conditions += " and lbx.lesson_date <= %(to_date)s"
		params["to_date"] = filters.get("to_date")

	rows = frappe.db.sql(
		"""
		select i.name as instructor, i.instructor_name,
			(select count(*) from `tabLesson Booking` lbx where lbx.instructor = i.name and {conditions}) as total_lessons,
			(select count(*) from `tabLesson Booking` lbx where lbx.instructor = i.name and lbx.status = 'Completed' and {conditions}) as completed,
			(select count(*) from `tabLesson Booking` lbx where lbx.instructor = i.name and lbx.status = 'No Show' and {conditions}) as no_shows,
			(select round(avg(rating), 1) from `tabLearner Feedback` f where f.instructor = i.name) as avg_rating
		from `tabDriving Instructor` i
		order by i.instructor_name asc
		""".format(conditions=conditions),
		params,
		as_dict=1,
	)

	passed = frappe.db.sql(
		"""
		select instructor, count(name) as tests_passed
		from `tabDriving Test`
		where result = 'Pass' and instructor is not null
		group by instructor
		""",
		as_dict=1,
	)
	passed_map = {row["instructor"]: row["tests_passed"] for row in passed}

	for row in rows:
		row["tests_passed"] = passed_map.get(row["instructor"], 0)
		row["total_lessons"] = row["total_lessons"] or 0
		row["completed"] = row["completed"] or 0
		row["no_shows"] = row["no_shows"] or 0
		row["avg_rating"] = round(row["avg_rating"] or 0, 1)

	return columns, rows
