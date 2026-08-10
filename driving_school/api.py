from __future__ import unicode_literals

import datetime

import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate, validate_email_address

from driving_school.utils import (
	get_demo_learner,
	get_instructor_for_user,
	get_learner_for_user,
	to_time,
)

ACTIVE_BOOKING_STATUSES = ["Requested", "Confirmed", "On Waitlist"]


def _get_learner():
	"""Learner for the current request.

	Logged-in users see their own linked Learner profile. The demo fallback
	(first Learner on file) applies only to anonymous visitors (Guest) so the
	portal works without login; logged-in users without a Learner profile are
	rejected instead of silently acting on the demo learner's account.
	"""
	user = frappe.session.user
	if user and user != "Guest":
		name = get_learner_for_user(user)
		if name:
			return name
		frappe.throw(
			_("Your user account is not linked to a Learner profile. Please contact the school."),
			frappe.PermissionError,
		)

	name = get_demo_learner()
	if name:
		return name

	frappe.throw(
		_("No learner records found yet. Add a Learner in the Driving School desk first."),
		frappe.PermissionError,
	)


def _resolve_bookings(bookings):
	for row in bookings:
		row["instructor_name"] = frappe.db.get_value(
			"Driving Instructor", row.instructor, "instructor_name"
		)
		row["vehicle_number"] = frappe.db.get_value(
			"Driving Vehicle", row.vehicle, "vehicle_number"
		)
	return bookings


# ---------------------------------------------------------------- summary & resources

@frappe.whitelist()
def get_learner_summary():
	learner = _get_learner()
	doc = frappe.get_cached_doc("Learner", learner)

	active_pkg = frappe.get_all(
		"Learner Package",
		filters={"learner": learner, "status": "Active"},
		fields=[
			"name",
			"package_name",
			"license_category",
			"lessons_count",
			"lessons_used",
			"discounted_amount",
			"balance_amount",
			"expiry_date",
		],
		limit_page_length=1,
	)

	upcoming = _resolve_bookings(
		frappe.get_all(
			"Lesson Booking",
			filters={
				"learner": learner,
				"lesson_date": [">=", nowdate()],
				"status": ["in", ACTIVE_BOOKING_STATUSES],
			},
			fields=["name", "lesson_date", "start_time", "instructor", "vehicle", "status"],
			order_by="lesson_date asc, start_time asc",
			limit_page_length=5,
		)
	)

	next_test = frappe.get_all(
		"Driving Test",
		filters={"learner": learner, "result": "Pending"},
		fields=["name", "test_type", "test_date"],
		order_by="test_date asc",
		limit_page_length=1,
	)

	completed = frappe.db.count("Lesson Booking", {"learner": learner, "status": "Completed"})
	no_shows = frappe.db.count("Lesson Booking", {"learner": learner, "status": "No Show"})

	return {
		"learner": {
			"name": learner,
			"learner_name": doc.learner_name,
			"status": doc.status,
			"training_stage": doc.training_stage,
			"category": doc.category,
			"mobile_number": doc.mobile_number,
		},
		"active_package": active_pkg[0] if active_pkg else None,
		"upcoming_lessons": upcoming,
		"next_test": next_test[0] if next_test else None,
		"completed_lessons": completed,
		"no_shows": no_shows,
	}


@frappe.whitelist()
def get_resources():
	"""Active instructors and vehicles for the booking form.

	Instructors that declare vehicle categories are shown only when the
	learner's category matches; unrestricted instructors are always shown.
	"""
	learner = _get_learner()
	learner_category = frappe.db.get_value("Learner", learner, "category")

	instructors = frappe.get_all(
		"Driving Instructor",
		filters={"is_active": 1, "employment_status": ["!=", "Resigned"]},
		fields=["name", "instructor_name", "photo"],
		order_by="instructor_name asc",
	)

	if learner_category:
		qualified = []
		for instructor in instructors:
			categories = frappe.get_all(
				"Instructor Vehicle Category",
				filters={"parent": instructor.name},
				pluck="category",
			)
			if not categories or learner_category in categories:
				qualified.append(instructor)
		instructors = qualified

	vehicles = frappe.get_all(
		"Driving Vehicle",
		filters={"is_active": 1, "status": "Available"},
		fields=["name", "vehicle_number", "vehicle_model", "vehicle_type", "transmission"],
		order_by="vehicle_number asc",
	)
	return {"instructors": instructors, "vehicles": vehicles}


# ---------------------------------------------------------------- booking

@frappe.whitelist()
def get_available_slots(lesson_date, instructor=None, vehicle=None):
	"""Return business-hour slots with availability for the logged-in learner."""
	learner = _get_learner()
	settings = frappe.get_single("Driving School Settings")

	start_t = to_time(settings.business_start_time) if settings.business_start_time else datetime.time(9, 0)
	end_t = to_time(settings.business_end_time) if settings.business_end_time else datetime.time(18, 0)
	duration = cint(settings.lesson_duration_minutes) or 60

	booked = frappe.get_all(
		"Lesson Booking",
		filters={"lesson_date": lesson_date, "status": ["in", ACTIVE_BOOKING_STATUSES]},
		fields=["learner", "instructor", "vehicle", "start_time"],
	)

	busy = {"learner": set(), "instructor": set(), "vehicle": set()}
	for b in booked:
		key = str(b.start_time)
		busy["learner"].add((b.learner, key))
		if b.instructor:
			busy["instructor"].add((b.instructor, key))
		if b.vehicle:
			busy["vehicle"].add((b.vehicle, key))

	# an instructor on approved leave is unavailable for the whole day
	instructor_on_leave = False
	if instructor:
		instructor_on_leave = bool(
			frappe.get_all(
				"Instructor Leave",
				filters={
					"instructor": instructor,
					"status": "Approved",
					"from_date": ["<=", lesson_date],
					"to_date": [">=", lesson_date],
				},
				limit_page_length=1,
			)
		)

	slots = []
	cur = datetime.datetime.combine(getdate(lesson_date), start_t)
	end_dt = datetime.datetime.combine(getdate(lesson_date), end_t)
	now = datetime.datetime.now()

	while cur < end_dt:
		key = cur.time().strftime("%H:%M:%S")
		available = True
		if instructor and (instructor, key) in busy["instructor"]:
			available = False
		if vehicle and (vehicle, key) in busy["vehicle"]:
			available = False
		if (learner, key) in busy["learner"]:
			available = False
		if instructor_on_leave:
			available = False
		if getdate(lesson_date) == nowdate() and cur <= now:
			available = False

		slots.append(
			{
				"start_time": key,
				"end_time": (cur + datetime.timedelta(minutes=duration)).time().strftime("%H:%M:%S"),
				"available": available,
			}
		)
		cur += datetime.timedelta(minutes=duration)

	return slots


@frappe.whitelist()
def book_lesson(lesson_date, start_time, instructor, vehicle, package=None, remarks=None):
	learner = _get_learner()

	if package:
		pkg = frappe.get_doc("Learner Package", package)
		if pkg.learner and pkg.learner != learner:
			frappe.throw(_("The selected package does not belong to your account."), frappe.PermissionError)

	settings = frappe.get_single("Driving School Settings")
	status = "Confirmed" if cint(settings.auto_confirm_portal_bookings) else "Requested"

	doc = frappe.get_doc(
		{
			"doctype": "Lesson Booking",
			"learner": learner,
			"package": package or None,
			"instructor": instructor,
			"vehicle": vehicle,
			"lesson_date": lesson_date,
			"start_time": start_time,
			"status": status,
			"remarks": remarks or "",
		}
	)
	doc.insert(ignore_permissions=True)
	return {"name": doc.name, "status": doc.status}


@frappe.whitelist()
def cancel_lesson(lesson_booking):
	learner = _get_learner()
	doc = frappe.get_doc("Lesson Booking", lesson_booking)

	if doc.learner != learner:
		frappe.throw(_("You can only cancel your own bookings."), frappe.PermissionError)
	if doc.status in ("Completed", "Cancelled"):
		frappe.throw(
			_("This booking cannot be cancelled in its current state ({0}).").format(doc.status)
		)

	doc.status = "Cancelled"
	doc.save(ignore_permissions=True)
	return {
		"name": doc.name,
		"status": doc.status,
		"cancellation_fee": doc.cancellation_fee,
	}


@frappe.whitelist()
def reschedule_lesson(lesson_booking, lesson_date, start_time, instructor=None, vehicle=None):
	learner = _get_learner()
	doc = frappe.get_doc("Lesson Booking", lesson_booking)

	if doc.learner != learner:
		frappe.throw(_("You can only reschedule your own bookings."), frappe.PermissionError)
	if doc.status not in ("Requested", "Confirmed"):
		frappe.throw(_("Only requested or confirmed bookings can be rescheduled."))

	doc.lesson_date = lesson_date
	doc.start_time = start_time
	doc.reminder_sent = 0
	if instructor:
		doc.instructor = instructor
	if vehicle:
		doc.vehicle = vehicle
	doc.save(ignore_permissions=True)

	return {"name": doc.name, "lesson_date": doc.lesson_date, "start_time": doc.start_time}


# ---------------------------------------------------------------- lessons & payments

@frappe.whitelist()
def get_my_lessons():
	learner = _get_learner()
	fields = [
		"name",
		"lesson_date",
		"start_time",
		"end_time",
		"instructor",
		"vehicle",
		"status",
		"instructor_notes",
		"remarks",
	]

	upcoming = _resolve_bookings(
		frappe.get_all(
			"Lesson Booking",
			filters={
				"learner": learner,
				"lesson_date": [">=", nowdate()],
				"status": ["in", ACTIVE_BOOKING_STATUSES],
			},
			fields=fields,
			order_by="lesson_date asc, start_time asc",
			limit_page_length=50,
		)
	)

	past = _resolve_bookings(
		frappe.get_all(
			"Lesson Booking",
			filters={
				"learner": learner,
				"status": ["in", ["Completed", "Cancelled", "No Show"]],
			},
			fields=fields,
			order_by="lesson_date desc, start_time desc",
			limit_page_length=50,
		)
	)

	return {"upcoming": upcoming, "past": past}


@frappe.whitelist()
def get_my_payments():
	learner = _get_learner()

	payments = frappe.get_all(
		"Learner Payment",
		filters={"learner": learner},
		fields=[
			"name",
			"payment_date",
			"amount",
			"mode_of_payment",
			"payment_type",
			"status",
			"reference_number",
		],
		order_by="payment_date desc",
		limit_page_length=100,
	)

	total_paid = frappe.db.sql(
		"""
		select ifnull(sum(amount), 0) from `tabLearner Payment`
		where learner = %(learner)s and docstatus < 2
			and status in ("Received", "Reconciled")
			and payment_type != "Refund"
		""",
		{"learner": learner},
	)[0][0]

	active_pkg = frappe.get_all(
		"Learner Package",
		filters={"learner": learner, "status": "Active"},
		fields=["name", "package_name", "balance_amount", "expiry_date", "lessons_used", "lessons_count"],
		limit_page_length=1,
	)

	return {
		"payments": payments,
		"total_paid": total_paid,
		"active_package": active_pkg[0] if active_pkg else None,
	}


@frappe.whitelist()
def request_payment(package, amount, mode_of_payment, reference_number=None):
	learner = _get_learner()

	pkg = frappe.get_doc("Learner Package", package)
	if pkg.learner != learner:
		frappe.throw(_("The selected package does not belong to your account."), frappe.PermissionError)

	doc = frappe.get_doc(
		{
			"doctype": "Learner Payment",
			"learner": learner,
			"package": package,
			"amount": amount,
			"mode_of_payment": mode_of_payment,
			"reference_number": reference_number or "",
			"payment_type": "Package Fee",
			"status": "Requested",
		}
	)
	doc.insert(ignore_permissions=True)
	return {"name": doc.name, "status": doc.status}


# ---------------------------------------------------------------- progress & tests

@frappe.whitelist()
def get_my_progress():
	learner = _get_learner()
	doc = frappe.get_cached_doc("Learner", learner)

	packages = frappe.get_all(
		"Learner Package",
		filters={"learner": learner},
		fields=[
			"name",
			"package_name",
			"license_category",
			"lessons_count",
			"lessons_used",
			"theory_class_hours",
			"test_attempts_included",
			"status",
			"expiry_date",
			"discounted_amount",
			"paid_amount",
			"balance_amount",
		],
		order_by="creation desc",
		limit_page_length=20,
	)

	mock_attempts = frappe.get_all(
		"Mock Test Attempt",
		filters={"learner": learner},
		fields=[
			"name",
			"category",
			"score_percent",
			"correct_answers",
			"total_questions",
			"result",
			"submitted_at",
		],
		order_by="submitted_at desc",
		limit_page_length=20,
	)

	driving_tests = frappe.get_all(
		"Driving Test",
		filters={"learner": learner},
		fields=["name", "test_type", "test_date", "result", "score", "retake_number"],
		order_by="test_date desc",
		limit_page_length=20,
	)

	attendance = frappe.get_all(
		"Theory Class Attendance",
		filters={"learner": learner},
		fields=["name", "theory_class", "class_title", "class_date", "status"],
		order_by="class_date desc",
		limit_page_length=50,
	)

	documents = frappe.get_all(
		"Learner Document",
		filters={"parent": learner},
		fields=["doc_type", "doc_number", "expiry_date", "is_verified"],
		order_by="idx asc",
	)

	return {
		"learner": {
			"name": learner,
			"learner_name": doc.learner_name,
			"status": doc.status,
			"training_stage": doc.training_stage,
			"category": doc.category,
		},
		"packages": packages,
		"mock_attempts": mock_attempts,
		"driving_tests": driving_tests,
		"attendance": attendance,
		"documents": documents,
	}


@frappe.whitelist()
def get_mock_questions(category, count=10):
	"""Return random active questions WITHOUT exposing correct answers."""
	_get_learner()
	count = cint(count) or 10

	questions = frappe.get_all(
		"Mock Test Question",
		filters={"is_active": 1, "category": category},
		fields=["name", "question", "option_a", "option_b", "option_c", "option_d", "topic", "marks"],
		order_by="rand()",
		limit_page_length=count,
	)
	return questions


@frappe.whitelist()
def submit_mock_test(category, answers):
	"""Score a mock test submission server-side."""
	learner = _get_learner()
	settings = frappe.get_single("Driving School Settings")
	pass_percent = cint(settings.mock_test_pass_percentage) or 60

	attempt = frappe.get_doc(
		{
			"doctype": "Mock Test Attempt",
			"learner": learner,
			"category": category,
			"pass_percentage": pass_percent,
		}
	)

	for answer in answers or []:
		attempt.append(
			"answers",
			{
				"question": answer.get("question"),
				"selected_answer": answer.get("selected_answer"),
			},
		)

	try:
		attempt.insert(ignore_permissions=True)
	except frappe.ValidationError:
		# Surface the real server-side validation message to the learner
		raise
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Driving School: mock test submit failed")
		frappe.throw(_("Could not save your test attempt. Please try again."))

	return {
		"name": attempt.name,
		"result": attempt.result,
		"score_percent": attempt.score_percent,
		"correct_answers": attempt.correct_answers,
		"total_questions": attempt.total_questions,
		"pass_percentage": attempt.pass_percentage,
		"answers": [
			{
				"question": a.question_text,
				"selected_answer": a.selected_answer,
				"correct_answer": a.correct_answer,
				"is_correct": a.is_correct,
			}
			for a in attempt.answers
		],
	}


# ---------------------------------------------------------------- feedback

@frappe.whitelist()
def submit_feedback(instructor, lesson=None, rating=5, comments=None):
	learner = _get_learner()

	if lesson:
		booking = frappe.get_doc("Lesson Booking", lesson)
		if booking.learner != learner:
			frappe.throw(_("You can only give feedback for your own lessons."), frappe.PermissionError)

	doc = frappe.get_doc(
		{
			"doctype": "Learner Feedback",
			"learner": learner,
			"lesson": lesson or None,
			"instructor": instructor,
			"rating": cint(rating) or 5,
			"comments": comments or "",
		}
	)
	doc.insert(ignore_permissions=True)
	return {"name": doc.name, "status": "Submitted"}


# ---------------------------------------------------------------- public forms

_VALID_CATEGORIES = {"Car", "Motorcycle", "Heavy Vehicle", "Bus", "Other"}


@frappe.whitelist()
def submit_enquiry(full_name, mobile_number, category, email=None, message=None):
	"""Public lead-capture form - creates an Enquiry (status New)."""
	full_name = (full_name or "").strip()
	mobile_number = (mobile_number or "").strip()
	category = (category or "").strip()

	if not full_name or not mobile_number:
		frappe.throw(_("Name and mobile number are required."))
	if category not in _VALID_CATEGORIES:
		frappe.throw(_("Please choose a valid category."))

	doc = frappe.get_doc(
		{
			"doctype": "Enquiry",
			"lead_name": full_name,
			"mobile_number": mobile_number,
			"email": (email or "").strip(),
			"category_of_interest": category,
			"source": "Website",
			"status": "New",
			"remarks": (message or "").strip(),
		}
	)
	doc.insert(ignore_permissions=True)
	return {"name": doc.name, "status": doc.status}


@frappe.whitelist()
def register_learner(full_name, mobile_number, email, category, password=None, city=None, address=None):
	"""Public self-registration - creates a Learner (and portal user when a password is given)."""
	full_name = (full_name or "").strip()
	mobile_number = (mobile_number or "").strip()
	email = (email or "").strip()
	category = (category or "").strip()

	if not full_name or not mobile_number or not email:
		frappe.throw(_("Name, mobile number and email are required."))
	if not validate_email_address(email):
		frappe.throw(_("Please enter a valid email address."))
	if category not in _VALID_CATEGORIES:
		frappe.throw(_("Please choose a valid category."))

	if password:
		# Create the portal user up front so the password is set at creation.
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": full_name,
				"new_password": password,
				"send_welcome_email": False,
				"home_page": "/portal-home",
				"roles": [{"role": "Learner"}],
			}
		)
		try:
			user.insert(ignore_permissions=True)
		except frappe.DuplicateEntryError:
			frappe.throw(_("An account with this email already exists. Please log in instead."))

	learner = frappe.get_doc(
		{
			"doctype": "Learner",
			"learner_name": full_name,
			"mobile_number": mobile_number,
			"email": email,
			"category": category,
			"city": (city or "").strip(),
			"address": (address or "").strip(),
			"source": "Website",
			"status": "Registered",
			"training_stage": "Not Started",
		}
	)
	learner.insert(ignore_permissions=True)

	# Log the new learner in immediately so they land on the portal, not the desk.
	# Skipped under the test runner: login_as commits the transaction, which
	# would break IntegrationTestCase rollback isolation.
	logged_in = False
	if password and not frappe.flags.in_test:
		try:
			from frappe.sessions import LoginManager

			LoginManager().login_as(email)
			logged_in = True
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Driving School: auto-login after registration failed")

	return {"name": learner.name, "learner_name": learner.learner_name, "logged_in": logged_in}


# ---------------------------------------------------------------- instructor portal

def _get_instructor():
	"""Driving Instructor linked to the logged-in user (no demo fallback)."""
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Please log in with your instructor account."), frappe.PermissionError)
	name = get_instructor_for_user(user)
	if not name:
		frappe.throw(
			_("Your user account is not linked to a Driving Instructor profile."),
			frappe.PermissionError,
		)
	return name


@frappe.whitelist()
def get_instructor_dashboard():
	"""Today's and upcoming lessons plus leave for the logged-in instructor."""
	instructor = _get_instructor()
	fields = ["name", "learner_name", "lesson_date", "start_time", "end_time", "vehicle", "status", "remarks"]

	todays_lessons = frappe.get_all(
		"Lesson Booking",
		filters={
			"instructor": instructor,
			"lesson_date": nowdate(),
			"status": ["in", ACTIVE_BOOKING_STATUSES],
		},
		fields=fields,
		order_by="start_time asc",
	)
	upcoming_lessons = frappe.get_all(
		"Lesson Booking",
		filters={
			"instructor": instructor,
			"lesson_date": [">", nowdate()],
			"status": ["in", ACTIVE_BOOKING_STATUSES],
		},
		fields=fields,
		order_by="lesson_date asc, start_time asc",
		limit_page_length=30,
	)
	leave = frappe.get_all(
		"Instructor Leave",
		filters={"instructor": instructor},
		fields=["name", "from_date", "to_date", "status", "reason"],
		order_by="from_date desc",
		limit_page_length=10,
	)

	for booking in todays_lessons + upcoming_lessons:
		booking["vehicle_number"] = frappe.db.get_value(
			"Driving Vehicle", booking.vehicle, "vehicle_number"
		)

	return {
		"instructor": instructor,
		"todays_lessons": todays_lessons,
		"upcoming_lessons": upcoming_lessons,
		"leave": leave,
	}


@frappe.whitelist()
def update_lesson_status(lesson_booking, status, instructor_notes=None):
	"""Mark an assigned lesson Completed or No Show from the instructor portal."""
	instructor = _get_instructor()
	if status not in ("Completed", "No Show"):
		frappe.throw(_("Invalid lesson status."))

	doc = frappe.get_doc("Lesson Booking", lesson_booking)
	if doc.instructor != instructor:
		frappe.throw(_("This lesson is not assigned to you."), frappe.PermissionError)
	if doc.status in ("Completed", "Cancelled", "No Show"):
		frappe.throw(_("This lesson is already {0}.").format(doc.status))
	if getdate(doc.lesson_date) > getdate(nowdate()):
		frappe.throw(_("You can only update lessons for today or earlier."))

	doc.status = status
	if instructor_notes:
		doc.instructor_notes = (instructor_notes or "").strip()
	doc.save(ignore_permissions=True)
	return {"name": doc.name, "status": doc.status}


@frappe.whitelist()
def request_instructor_leave(from_date, to_date, reason=None):
	"""Submit an instructor leave request from the portal."""
	instructor = _get_instructor()
	doc = frappe.get_doc(
		{
			"doctype": "Instructor Leave",
			"instructor": instructor,
			"from_date": from_date,
			"to_date": to_date,
			"reason": (reason or "").strip(),
			"status": "Requested",
		}
	)
	doc.insert(ignore_permissions=True)
	return {"name": doc.name, "status": doc.status}
