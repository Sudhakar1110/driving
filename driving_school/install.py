from __future__ import unicode_literals

import os

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


def before_migrate():
	"""Purge the stale Redis module-map cache and rebuild it from disk.

	Frappe caches the app -> module map (built from each app's modules.txt)
	in Redis and reuses that cache verbatim on every startup / migrate. If the
	cache was built while driving_school had a broken layout (modules.txt
	missing or at the wrong path), frappe.model.sync.sync_for silently finds
	zero modules for this app - so migrate completes with NO doctypes, NO
	reports and NO workspace, and no error at all.

	This hook runs (fresh from disk, bypassing the stale cache) right before
	the schema sync, so the sync rebuilds the map from disk and the app syncs.
	"""
	try:
		frappe.cache.delete_value(["app_modules", "installed_app_modules", "all_apps"])
		frappe.setup_module_map(include_all_apps=True)
		modules = (frappe.local.app_modules or {}).get("driving_school")
		print("driving_school: module map rebuilt -> {}".format(modules))

		# show exactly where Python loads the app from (self-diagnosing migrate)
		try:
			pkg_file = getattr(frappe.get_module("driving_school"), "__file__", "?")
			mod = frappe.get_module("driving_school.driving_school")
			mod_file = getattr(mod, "__file__", "?")
			mfolder = os.path.dirname(mod_file or "") if mod_file else ""
			print("driving_school: package at ->", pkg_file)
			print("driving_school: module folder ->", mfolder)
			if not os.path.isdir(os.path.join(mfolder, "doctype")):
				print(
					"driving_school: WARNING - no doctype/ folder at", mfolder,
					"- Python is loading a stale copy of the app."
					" Re-run: uv pip install --upgrade -e apps/driving_school"
				)
		except Exception as e:
			print("driving_school: could not probe module folder:", type(e).__name__, e)

		if not modules:
			print(
				"driving_school: WARNING - modules.txt was not found on disk. "
				"Pull the latest code (git reset --hard upstream/main) and re-run migrate."
			)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "driving_school: before_migrate cache purge failed")


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
