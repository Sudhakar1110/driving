// Register the Calendar view for Lesson Booking on the Desk.
// Loaded via app_include_js; registration is guarded and idempotent.

frappe.ready(() => {
	if (frappe.views && frappe.views.calendar && !frappe.views.calendar["Lesson Booking"]) {
		frappe.views.calendar["Lesson Booking"] = {
			field_map: {
				start: "lesson_date",
				end: "lesson_date",
				id: "name",
				title: "learner_name",
				allDay: "allDay",
			},
			get_events_method: "frappe.desk.calendar.get_events",
		};
	}
});
