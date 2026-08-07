from __future__ import unicode_literals

import frappe


ROLES = [
	{
		"role": "Driving School Admin",
		"desk_access": 1,
		"description": "Full access to the Driving School app",
	},
	{
		"role": "Driving School Manager",
		"desk_access": 1,
		"description": "Branch / franchise manager with operational access",
	},
	{
		"role": "Driving Instructor",
		"desk_access": 1,
		"description": "Driving instructors - view lessons and update their classes",
	},
	{
		"role": "Driving School Accounts",
		"desk_access": 1,
		"description": "Accounts - payments, invoices and financial reports",
	},
	{
		"role": "Learner",
		"desk_access": 0,
		"description": "Learner portal users (self-service booking and payments)",
	},
]


def after_install():
	create_roles()
	create_default_settings()
	set_learner_home_page()


def before_uninstall():
	delete_roles()


def create_roles():
	"""Create the custom roles used by the app."""
	for r in ROLES:
		if not frappe.db.exists("Role", r["role"]):
			try:
				frappe.get_doc(
					{
						"doctype": "Role",
						"role_name": r["role"],
						"desk_access": r["desk_access"],
						"description": r["description"],
					}
				).insert(ignore_permissions=True)
			except Exception:
				frappe.log_error(frappe.get_traceback(), "Driving School: role creation failed")


def create_default_settings():
	"""Create the single settings document with sensible defaults."""
	if not frappe.db.exists("Driving School Settings", "Driving School Settings"):
		try:
			settings = frappe.get_single("Driving School Settings")
			settings.save(ignore_permissions=True)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Driving School: settings creation failed")


def set_learner_home_page():
	"""Point portal learners at the learner dashboard after login."""
	try:
		if frappe.db.exists("Role", "Learner"):
			frappe.db.set_value("Role", "Learner", "home_page", "/portal-home")
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Driving School: home page update failed")


def delete_roles():
	"""Remove custom roles on uninstall (only if no users are assigned)."""
	for r in ROLES:
		if not frappe.db.exists("Role", r["role"]):
			continue
		try:
			assigned = frappe.db.count("Has Role", {"role": r["role"]})
			if not assigned:
				frappe.delete_doc("Role", r["role"], ignore_permissions=True)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Driving School: role deletion failed")
