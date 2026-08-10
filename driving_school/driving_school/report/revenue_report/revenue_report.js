// Copyright (c) 2024, Driving School and contributors
// For license information, please see license.txt

frappe.query_reports["Revenue Report"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
		},
		{
			"fieldname": "branch",
			"label": __("Branch"),
			"fieldtype": "Link",
			"options": "Driving School Branch",
		},
		{
			"fieldname": "payment_type",
			"label": __("Payment Type"),
			"fieldtype": "Select",
			"options": ["", "Package Fee", "Installment", "Add-on Lesson", "Test Fee", "Refund", "Other"],
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": ["", "Requested", "Received", "Reconciled", "Cancelled"],
		},
	],
};
