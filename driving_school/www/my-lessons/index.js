frappe.ready(() => {
	if (!$("#upcoming-list").length) return;

	load();

	function load() {
		frappe.call({
			method: "driving_school.api.get_my_lessons",
			callback: (r) => {
				if (r.exc) {
					showMsg("Could not load your lessons. Please try again.", "danger");
					return;
				}
				render(r.message || {});
			},
		});
	}

	function render(data) {
		renderList("#upcoming-list", data.upcoming || [], true);
		renderList("#past-list", data.past || [], false);
	}

	function renderList(selector, items, actionable) {
		const $list = $(selector).empty();
		if (!items.length) {
			$list.append(
				'<li class="list-group-item text-muted">' +
					(actionable ? "No upcoming lessons. <a href='/book-lesson'>Book one now</a>." : "No past lessons yet.") +
					"</li>"
			);
			return;
		}

		items.forEach((b) => {
			const statusClass =
				b.status === "Completed"
					? "badge-success"
					: b.status === "Cancelled" || b.status === "No Show"
					? "badge-danger"
					: b.status === "Confirmed"
					? "badge-primary"
					: "badge-warning";

			const $li = $('<li class="list-group-item"></li>');
			$li.append(
				'<div class="d-flex justify-content-between align-items-center">' +
					'<div><strong>' +
					b.lesson_date +
					"</strong> at " +
					b.start_time +
					(b.end_time ? " - " + b.end_time : "") +
					"<div class=\"text-muted small\">" +
					(b.instructor_name || "Instructor") +
					" &middot; " +
					(b.vehicle_number || "Vehicle") +
					"</div>" +
					(b.instructor_notes
						? '<div class="small mt-1"><i class="fa fa-comment-o"></i> ' + b.instructor_notes + "</div>"
						: "") +
					"</div>" +
					'<div class="text-right"><span class="badge ' +
					statusClass +
					'">' +
					b.status +
					"</span></div></div>"
			);

			if (actionable && (b.status === "Confirmed" || b.status === "Requested")) {
				const $actions = $(
					'<div class="mt-2">' +
						'<button class="btn btn-sm btn-outline-danger mr-1" data-action="cancel" data-name="' +
						b.name +
						'">' +
						__("Cancel") +
						'</button>' +
						'<button class="btn btn-sm btn-outline-primary" data-action="resched" data-name="' +
						b.name +
						'">' +
						__("Reschedule") +
						"</button></div>"
				);
				$li.append($actions);
			}

			if (!actionable && b.status === "Completed") {
				$li.append(
					'<button class="btn btn-sm btn-outline-success mt-2" data-action="feedback" data-name="' +
						b.name +
						'" data-instructor="' +
						(b.instructor || "") +
						'">' +
						__("Give Feedback") +
						"</button>"
				);
			}
			$list.append($li);
		});
	}

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
		});
	});

	$(document).on("click", '[data-action="resched"]', (e) => {
		const $btn = $(e.currentTarget);
		const name = $btn.data("name");
		const $li = $btn.closest("li");

		if ($li.find(".ds-resched").length) {
			$li.find(".ds-resched").remove();
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
				name +
				'">' +
				__("Save") +
				"</button></div></div></div>"
		);
		$li.append($form);
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
		});
	});

	$(document).on("click", '[data-action="feedback"]', (e) => {
		const $btn = $(e.currentTarget);
		const $li = $btn.closest("li");
		if ($li.find(".ds-feedback").length) {
			$li.find(".ds-feedback").remove();
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
				$btn.data("name") +
				'" data-instructor="' +
				($btn.data("instructor") || "") +
				'">' +
				__("Submit Feedback") +
				"</button></div>"
		);
		$li.append($form);
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
		});
	});

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
});
