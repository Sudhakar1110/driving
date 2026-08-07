from __future__ import unicode_literals

import frappe
from frappe import _


def get_settings():
	"""Cached single settings document."""
	return frappe.get_single("Driving School Settings")


def get_learner_for_user(user=None):
	"""Return the Learner name linked to a portal user, or None."""
	user = user or frappe.session.user
	if not user or user == "Guest":
		return None

	name = frappe.db.get_value("Learner", {"email": user}, "name")
	if not name:
		name = frappe.db.get_value("Learner", {"user": user}, "name")
	return name


def send_email(recipients, subject, message, reference_doctype=None, reference_name=None):
	"""Safe email helper - logs failures instead of raising."""
	if not recipients:
		return
	try:
		frappe.sendmail(
			recipients=recipients,
			subject=subject,
			message=message,
			reference_doctype=reference_doctype,
			reference_name=reference_name,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Driving School: email sending failed")


def get_admin_email():
	"""Email used for system alerts (fallback: Administrator user)."""
	settings = get_settings()
	if settings.admin_email:
		return settings.admin_email
	return frappe.db.get_value("User", "Administrator", "email")


def erpnext_installed():
	"""True when ERPNext (Accounts) is available - used for optional integrations."""
	return bool(frappe.db.exists("Module Def", "ERPNext"))
