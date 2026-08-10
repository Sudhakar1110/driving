frappe.ready(() => {
	if (!$("#upcoming-list").length) return;

	load();

	function load() {
		frappe.call({
			method: "driving_school.api.get_my_lessons",
			callback: (r) => {
				if (r.exc) {
					showMsg(
						__("Could not load your lessons: ") +
							(r._server_messages ? r._server_messages.join(" ") : __("server error")),
						"danger"
					);
					return;
				}
				render(r.message || {});
			},
			error: () => showMsg(__("Could not load your lessons. Please try again."), "danger"),
		});
	}

	const STATUS_CLASS = {
		Completed: "success",
		Cancelled: "danger",
		"No Show": "danger",
		Confirmed: "primary",
		Requested: "warning",
		"On Waitlist": "info",
	};

	function render(data) {
		const upcoming = data.upcoming || [];
		const past = data.past || [];
		$("#l-upcoming").text(upcoming.length);
		$("#l-completed").text(past.filter((b) => b.status === "Completed").length);
		$("#l-cancelled").text(past.filter((b) => b.status === "Cancelled").length);
		$("#l-noshow").text(past.filter((b) => b.status === "No Show").length);

		renderList("#upcoming-list", upcoming, true);
		renderList("#past-list", past, false);
	}

	function renderList(selector, items, actionable) {
		const $list = $(selector).empty();
		if (!items.length) {
			$list.append(
				'<div class="text-center text-muted py-4">' +
					(actionable
						? __("No upcoming lessons. ") + '<a href="/book-lesson">' + __("Book one now") + "</a>."
						: __("No past lessons yet.")) +
					"</div>"
			);
			return;
		}
		items.forEach((b) => $list.append(lessonItem(b, actionable)));
	}

	function lessonItem(b, actionable) {
		const date = dateParts(b.lesson_date);
		const past = !actionable;
		const $item = $('<div class="ds-lesson-item"></div>');
		$item.append(
			'<div class="ds-lesson-date"><div class="ds-date-chip' +
				(past ? " muted" : "") +
				'"><span class="ds-date-day">' +
				date.day +
				'</span><span class="ds-date-month">' +
				date.month +
				"</span></div></div>"
		);

		const $body = $('<div class="ds-lesson-body"></div>');
		$body.append(
			'<div class="d-flex justify-content-between align-items-start flex-wrap">' +
				"<div>" +
				'<div class="ds-lesson-time">' +
				fmtTime(b.start_time) +
				(b.end_time ? " - " + fmtTime(b.end_time) : "") +
				'</div><div class="text-muted small">' +
				date.full +
				'</div><div class="text-muted small mt-1">' +
				esc(b.instructor_name || __("Instructor")) +
				" &middot; " +
				esc(b.vehicle_number || __("Vehicle")) +
				"</div>" +
				(b.instructor_notes
					? '<div class="ds-note small mt-2">' + esc(b.instructor_notes) + "</div>"
					: "") +
				"</div>" +
				'<span class="badge badge-' +
				(STATUS_CLASS[b.status] || "secondary") +
				'">' +
				esc(b.status) +
				"</span></div>"
		);

		if (actionable && (b.status === "Confirmed" || b.status === "Requested")) {
			$body.append(
				'<div class="mt-2">' +
					'<button class="btn btn-sm btn-outline-danger mr-1" data-action="cancel" data-name="' +
					esc(b.name) +
					'">' +
					__("Cancel") +
					'</button><button class="btn btn-sm btn-outline-primary" data-action="resched" data-name="' +
					esc(b.name) +
					'">' +
					__("Reschedule") +
					"</button></div>"
			);
		}
		if (!actionable && b.status === "Completed") {
			$body.append(
				'<button class="btn btn-sm btn-outline-success mt-2" data-action="feedback" data-name="' +
					esc(b.name) +
					'" data-instructor="' +
					esc(b.instructor || "") +
					'">' +
					__("Give Feedback") +
					"</button>"
			);
		}
		$item.append($body);
		return $item;
	}

	// ---------------------------------------------------------------- helpers

	function dateParts(iso) {
		const d = new Date(String(iso || "").slice(0, 10) + "T00:00:00");
		if (isNaN(d.getTime())) return { day: "—", month: "", full: String(iso || "—") };
		return {
			day: String(d.getDate()).padStart(2, "0"),
			month: d.toLocaleString("en", { month: "short" }).toUpperCase(),
			full: d.toLocaleDateString(undefined, {
				weekday: "short",
				day: "numeric",
				month: "short",
				year: "numeric",
			}),
		};
	}

	function fmtTime(t) {
		const parts = String(t || "").split(":");
		if (parts.length >= 2) return parts[0].padStart(2, "0") + ":" + parts[1];
		return String(t || "");
	}

	function esc(v) {
		return String(v == null ? "" : v).replace(/[&<>"']/g, (c) =>
			({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
		);
	}

	function showMsg(msg, type) {
		const types = { danger: "alert-danger", success: "alert-success", warning: "alert-warning", info: "alert-info" };
		$("#ds-msg").html(
			'<div class="alert ' +
				(types[type] || "alert-info") +
				' alert-dismissible fade show" role="alert">' +
				msg +
				'<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'
		);
	}

	// ---------------------------------------------------------------- actions

	$(document).on("click", '[data-action="cancel"]', (e) => {
		const $btn = $(e.currentTarget);
		if (!confirm(__("Cancel this lesson?"))) return;
		frappe.call({
			method: "driving_school.api.cancel_lesson",
			args: { lesson_booking: $btn.data("name") },
			callback: (r) => {
				if (r.exc) {
					showMsg(
						r._server_messages ? r._server_messages.join("<br>") : __("Could not cancel the lesson."),
						"danger"
					);
					return;
				}
				showMsg(
					__("Lesson cancelled.") +
						(r.message.cancellation_fee
							? " " + __("Cancellation fee") + ": " + r.message.cancellation_fee
							: ""),
					"success"
				);
				load();
			},
			error: () => showMsg(__("Could not cancel the lesson."), "danger"),
		});
	});

	$(document).on("click", '[data-action="resched"]', (e) => {
		const $btn = $(e.currentTarget);
		const name = $btn.data("name");
		const $item = $btn.closest(".ds-lesson-item");

		if ($item.find(".ds-resched").length) {
			$item.find(".ds-resched").remove();
			return;
		}

		const $form = $(
			'<div class="ds-resched card card-body bg-light mt-2">' +
				'<div class="row">' +
				'<div class="col-md-4 form-group mb-2"><label>' +
				__("Date") +
				'</label><input type="date" class="form-control form-control-sm r-date" value="' +
				frappe.datetime.get_today() +
				'"></div>' +
				'<div class="col-md-4 form-group mb-2"><label>' +
				__("Time") +
				'</label><input type="time" class="form-control form-control-sm r-time" value="09:00"></div>' +
				'<div class="col-md-4 d-flex align-items-end mb-2">' +
				'<button class="btn btn-sm btn-success r-save" data-name="' +
				esc(name) +
				'">' +
				__("Save") +
				"</button></div></div></div>"
		);
		$item.find(".ds-lesson-body").append($form);
	});

	$(document).on("click", ".r-save", (e) => {
		const $btn = $(e.currentTarget);
		const $form = $btn.closest(".ds-resched");
		const date = $form.find(".r-date").val();
		const time = $form.find(".r-time").val();
		if (!date || !time) {
			showMsg(__("Pick a date and time."), "warning");
			return;
		}
		frappe.call({
			method: "driving_school.api.reschedule_lesson",
			args: { lesson_booking: $btn.data("name"), lesson_date: date, start_time: time },
			callback: (r) => {
				if (r.exc) {
					showMsg(
						r._server_messages ? r._server_messages.join("<br>") : __("Could not reschedule."),
						"danger"
					);
					return;
				}
				showMsg(__("Lesson rescheduled."), "success");
				load();
			},
			error: () => showMsg(__("Could not reschedule."), "danger"),
		});
	});

	$(document).on("click", '[data-action="feedback"]', (e) => {
		const $btn = $(e.currentTarget);
		const $item = $btn.closest(".ds-lesson-item");
		if ($item.find(".ds-feedback").length) {
			$item.find(".ds-feedback").remove();
			return;
		}

		const ratingOptions = "12345"
			.split("")
			.map((n) => '<option value="' + n + '"' + (n === "5" ? " selected" : "") + ">" + n + "</option>")
			.join("");

		const $form = $(
			'<div class="ds-feedback card card-body bg-light mt-2">' +
				'<div class="form-group mb-2"><label>' +
				__("Rating") +
				'</label><select class="form-control form-control-sm f-rating">' +
				ratingOptions +
				"</select></div>" +
				'<div class="form-group mb-2"><label>' +
				__("Comments") +
				'</label><textarea class="form-control form-control-sm f-comments" rows="2"></textarea></div>' +
				'<button class="btn btn-sm btn-success f-save" data-name="' +
				esc($btn.data("name")) +
				'" data-instructor="' +
				esc($btn.data("instructor") || "") +
				'">' +
				__("Submit Feedback") +
				"</button></div>"
		);
		$item.find(".ds-lesson-body").append($form);
	});

	$(document).on("click", ".f-save", (e) => {
		const $btn = $(e.currentTarget);
		const $form = $btn.closest(".ds-feedback");
		const rating = $form.find(".f-rating").val();
		const comments = $form.find(".f-comments").val();
		frappe.call({
			method: "driving_school.api.submit_feedback",
			args: {
				lesson: $btn.data("name"),
				instructor: $btn.data("instructor"),
				rating: rating,
				comments: comments,
			},
			callback: (r) => {
				if (r.exc) {
					showMsg(
						r._server_messages ? r._server_messages.join("<br>") : __("Could not submit feedback."),
						"danger"
					);
					return;
				}
				showMsg(__("Thank you for your feedback!"), "success");
				$form.empty().append('<span class="text-success">' + __("Feedback submitted.") + "</span>");
			},
			error: () => showMsg(__("Could not submit feedback."), "danger"),
		});
	});
});
