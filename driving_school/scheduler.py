from __future__ import unicode_literals

import datetime

import frappe
from frappe import _
from frappe.utils import add_days, cint, getdate, now_datetime, nowdate

from driving_school.utils import get_admin_email, get_settings, send_email, to_time


def daily():
	try:
		send_lesson_reminders()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Driving School: lesson reminders failed")
	try:
		alert_expiring_documents()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Driving School: document expiry alerts failed")
	try:
		alert_expiring_vehicles()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Driving School: vehicle expiry alerts failed")
	try:
		alert_package_expiry()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Driving School: package expiry alerts failed")


def hourly():
	try:
		send_short_lesson_reminders()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Driving School: short reminders failed")


# ---------------------------------------------------------------- reminders

def send_lesson_reminders():
	"""Email learners 24h (settings.reminder_hours) before their lesson."""
	settings = get_settings()
	if not cint(settings.enable_email_reminders):
		return

	hours_ahead = cint(settings.reminder_hours) or 24
	target_dt = now_datetime() + datetime.timedelta(hours=hours_ahead)

	bookings = frappe.get_all(
		"Lesson Booking",
		filters={
			"lesson_date": getdate(target_dt),
			"status": ["in", ["Requested", "Confirmed"]],
			"reminder_sent": 0,
		},
		fields=["name", "learner", "lesson_date", "start_time", "instructor"],
	)

	for booking in bookings:
		learner = frappe.get_cached_doc("Learner", booking.learner)
		instructor_name = frappe.db.get_value(
			"Driving Instructor", booking.instructor, "instructor_name"
		)
		message = frappe.render_template(
			"""<p>Dear <b>{{ learner_name }}</b>,</p>
			<p>Reminder: you have a driving lesson on <b>{{ lesson_date }}</b>
			at <b>{{ start_time }}</b> with <b>{{ instructor_name }}</b>.</p>
			<p>Please arrive on time with your learner documents.</p>""",
			{
				"learner_name": learner.learner_name,
				"lesson_date": booking.lesson_date,
				"start_time": booking.start_time,
				"instructor_name": instructor_name or "the school",
			},
		)
		send_email(
			learner.email,
			_("Lesson Reminder - {0} {1}").format(booking.lesson_date, booking.start_time),
			message,
			reference_doctype="Lesson Booking",
			reference_name=booking.name,
		)
		frappe.db.set_value("Lesson Booking", booking.name, "reminder_sent", 1)


def send_short_lesson_reminders():
	"""Email learners a short notice reminder (settings.short_reminder_hours)."""
	settings = get_settings()
	if not cint(settings.enable_email_reminders):
		return

	hours_ahead = cint(settings.short_reminder_hours) or 2
	target_dt = now_datetime() + datetime.timedelta(hours=hours_ahead)

	bookings = frappe.get_all(
		"Lesson Booking",
		filters={
			"lesson_date": getdate(target_dt),
			"status": ["in", ["Requested", "Confirmed"]],
		},
		fields=["name", "learner", "lesson_date", "start_time", "instructor"],
	)

	for booking in bookings:
		if not is_within_window(booking.lesson_date, booking.start_time, target_dt, hours_ahead):
			continue
		learner = frappe.get_cached_doc("Learner", booking.learner)
		instructor_name = frappe.db.get_value(
			"Driving Instructor", booking.instructor, "instructor_name"
		)
		message = frappe.render_template(
			"""<p>Hi <b>{{ learner_name }}</b>,</p>
			<p>Your lesson starts soon at <b>{{ start_time }}</b> with <b>{{ instructor_name }}</b>.
			See you there!</p>""",
			{
				"learner_name": learner.learner_name,
				"start_time": booking.start_time,
				"instructor_name": instructor_name or "the school",
			},
		)
		send_email(
			learner.email,
			_("Lesson starting soon"),
			message,
			reference_doctype="Lesson Booking",
			reference_name=booking.name,
		)


def is_within_window(lesson_date, start_time, target_dt, hours_ahead):
	"""True when the lesson start falls within [target, target + lesson window]."""
	if not start_time:
		return False
	start_dt = datetime.datetime.combine(getdate(lesson_date), to_time(start_time))
	return target_dt <= start_dt < target_dt + datetime.timedelta(hours=1)


# ---------------------------------------------------------------- expiry alerts

def alert_expiring_documents():
	"""Alert admin about medical certificates expiring in the next 14 days."""
	expiry = add_days(nowdate(), 14)
	learners = frappe.get_all(
		"Learner",
		filters={
			"medical_certificate_expiry": ["between", [nowdate(), expiry]],
			"status": ["not in", ["Dropped"]],
		},
		fields=["name", "learner_name", "medical_certificate_expiry"],
		limit_page_length=100,
	)
	if not learners:
		return

	rows = "".join(
		"<li>{0} ({1}) - {2}</li>".format(
			l.learner_name, l.name, l.medical_certificate_expiry
		)
		for l in learners
	)
	send_email(
		get_admin_email(),
		_("Medical certificates expiring soon"),
		"<p>The following learners have medical certificates expiring within 14 days:</p><ul>{0}</ul>".format(rows),
	)


def alert_expiring_vehicles():
	"""Alert admin about vehicle insurance / permit / fitness expiry in next 30 days."""
	expiry = add_days(nowdate(), 30)
	vehicles = frappe.get_all(
		"Driving Vehicle",
		filters=[
			["insurance_expiry", "between", [nowdate(), expiry]],
			["is_active", "=", 1],
		],
		fields=["name", "vehicle_number", "insurance_expiry"],
		limit_page_length=100,
	)
	if not vehicles:
		return

	rows = "".join(
		"<li>{0} ({1}) - insurance {2}</li>".format(
			v.vehicle_number, v.name, v.insurance_expiry
		)
		for v in vehicles
	)
	send_email(
		get_admin_email(),
		_("Vehicle insurance expiring soon"),
		"<p>The following vehicles have insurance expiring within 30 days:</p><ul>{0}</ul>".format(rows),
	)


def alert_package_expiry():
	"""Email learners whose package expires in the next 7 days."""
	expiry = add_days(nowdate(), 7)
	packages = frappe.get_all(
		"Learner Package",
		filters={
			"expiry_date": ["between", [nowdate(), expiry]],
			"status": "Active",
		},
		fields=["name", "package_name", "learner", "lessons_used", "lessons_count", "expiry_date"],
		limit_page_length=100,
	)
	for pkg in packages:
		if not pkg.learner:
			continue
		learner = frappe.get_cached_doc("Learner", pkg.learner)
		if not learner.email:
			continue
		message = frappe.render_template(
			"""<p>Hi <b>{{ learner_name }}</b>,</p>
			<p>Your package <b>{{ package_name }}</b> expires on <b>{{ expiry_date }}</b>.
			You have used {{ lessons_used }} of {{ lessons_count }} lessons.</p>
			<p>Please contact the school to complete or extend your package.</p>""",
			{
				"learner_name": learner.learner_name,
				"package_name": pkg.package_name,
				"expiry_date": pkg.expiry_date,
				"lessons_used": pkg.lessons_used,
				"lessons_count": pkg.lessons_count,
			},
		)
		send_email(
			learner.email,
			_("Your package expires soon"),
			message,
			reference_doctype="Learner Package",
			reference_name=pkg.name,
		)
