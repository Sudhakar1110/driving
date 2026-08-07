// Copyright (c) 2024, Driving School and contributors
// For license information, please see license.txt

frappe.query_reports["Outstanding Receivables"] = {
	"filters": [
		{
			"fieldname": "branch",
			"label": __("Branch"),
			"fieldtype": "Link",
			"options": "Driving School Branch",
		},
	],
};
