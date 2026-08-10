from __future__ import unicode_literals

import datetime

import frappe
from frappe import _
from frappe.utils import cint


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


def get_demo_learner():
	"""First Learner on file - the public demo identity.

	This fallback is reserved for anonymous (Guest) visitors only; logged-in
	users are never resolved through it.
	"""
	return frappe.db.get_value("Learner", {}, "name", order_by="creation asc")


def get_instructor_for_user(user=None):
	"""Return the Driving Instructor linked to a user, or None."""
	user = user or frappe.session.user
	if not user or user == "Guest":
		return None

	name = frappe.db.get_value("Driving Instructor", {"user": user}, "name")
	if not name:
		name = frappe.db.get_value("Driving Instructor", {"email": user}, "name")
	return name


def get_or_create_learner_for_user(user=None):
	"""Learner linked to a logged-in user, auto-created when missing.

	Self-service portal: logging in with an account that has no Learner
	profile creates one automatically (subject to the
	``auto_create_learner_on_login`` setting), so every user gets a working
	portal immediately - no manual linking required. Anonymous visitors are
	never auto-created. Returns the Learner name or None.
	"""
	user = user or frappe.session.user
	if not user or user == "Guest":
		return None

	name = get_learner_for_user(user)
	if name:
		return name

	if not cint(get_settings().auto_create_learner_on_login):
		return None

	full_name = frappe.db.get_value("User", user, "full_name") or user
	mobile_no = frappe.db.get_value("User", user, "mobile_no") or ""

	doc = frappe.get_doc(
		{
			"doctype": "Learner",
			"learner_name": full_name,
			"mobile_number": mobile_no,
			"email": user,
			"category": "Car",
			"source": "Portal",
			"status": "Registered",
			"training_stage": "Not Started",
		}
	)
	try:
		doc.insert(ignore_permissions=True, ignore_mandatory=True)
		return doc.name
	except Exception:
		# e.g. a concurrent request created the profile in the meantime
		frappe.log_error(frappe.get_traceback(), "Driving School: auto-create learner failed")
		return get_learner_for_user(user)


def is_logged_in_user_instructor():
	"""True when the current session user is linked to a Driving Instructor."""
	user = frappe.session.user
	if not user or user == "Guest":
		return False
	return bool(get_instructor_for_user(user))


def get_learner_for_context():
	"""Learner for the current request (public demo mode).

	Logged-in users only ever see their own linked Learner profile. The demo
	fallback - the first Learner on file - applies ONLY to anonymous visitors
	(Guest), so logged-in staff can never operate on the demo learner's
	account. Returns ``(learner_name, learner_display_name)`` or ``(None, None)``
	when there is no learner to show.
	"""
	user = frappe.session.user
	if user and user != "Guest":
		name = get_or_create_learner_for_user(user)
		if name:
			return name, frappe.db.get_value("Learner", name, "learner_name")
		return None, None

	# Anonymous visitor -> public demo mode
	name = get_demo_learner()
	if name:
		return name, frappe.db.get_value("Learner", name, "learner_name")
	return None, None


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


def to_time(value):
	"""Convert a Frappe Time value to datetime.time.

	Frappe does not expose ``frappe.utils.to_time``, so this local helper is used.
	Accepts a ``datetime.time``, a ``datetime.timedelta`` (as returned by the
	MariaDB driver for TIME columns) or a "HH:MM[:SS]" string.
	"""
	if isinstance(value, datetime.time):
		return value
	if isinstance(value, datetime.timedelta):
		seconds = int(value.total_seconds()) % 86400
		return (datetime.datetime(2000, 1, 1) + datetime.timedelta(seconds=seconds)).time()
	if isinstance(value, str):
		value = value.strip()
		for fmt in ("%H:%M:%S", "%H:%M"):
			try:
				return datetime.datetime.strptime(value, fmt).time()
			except ValueError:
				continue
	return value
