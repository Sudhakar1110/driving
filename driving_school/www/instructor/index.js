frappe.ready(() => {
	if (!$("#i-today").length) return;

	load();

	function load() {
		frappe.call({
			method: "driving_school.api.get_instructor_dashboard",
			callback: (r) => {
				if (r.exc) {
					showMsg(
						r._server_messages ? r._server_messages.join("<br>") : __("Could not load your dashboard."),
						"danger"
					);
					return;
				}
				render(r.message || {});
			},
		});
	}

	function render(data) {
		const todays = data.todays_lessons || [];
		const upcoming = data.upcoming_lessons || [];
		const leave = data.leave || [];

		$("#i-today").text(todays.length);
		$("#i-upcoming").text(upcoming.length);
		$("#i-leave").text(leave.length);
		$("#i-pending").text(leave.filter((l) => l.status === "Requested").length);

		renderLessons("#today-list", todays, true);
		renderLessons("#upcoming-list", upcoming, false);

		const $leave = $("#leave-list").empty();
		if (!leave.length) {
			$leave.append('<li class="list-group-item text-muted">' + __("No leave records.") + "</li>");
		}
		leave.forEach((l) => {
			const badge = l.status === "Approved" ? "badge-success" : l.status === "Rejected" ? "badge-danger" : "badge-warning";
			$leave.append(
				'<li class="list-group-item d-flex justify-content-between align-items-center flex-wrap">' +
					"<span><strong>" + l.from_date + "</strong> → " + l.to_date +
					(l.reason ? '<div class="text-muted small">' + l.reason + "</div>" : "") +
					'</span><span class="badge ' + badge + '">' + l.status + "</span></li>"
			);
		});
	}

	function renderLessons(selector, items, actionable) {
		const $list = $(selector).empty();
		if (!items.length) {
			$list.append(
				'<li class="list-group-item text-muted">' +
					(actionable ? __("No lessons scheduled for today.") : __("No upcoming lessons.")) +
					"</li>"
			);
			return;
		}
		items.forEach((b) => {
			const $li = $(
				'<li class="list-group-item"><div class="d-flex justify-content-between align-items-center flex-wrap">' +
					"<div><strong>" + b.start_time + "</strong>" +
					(b.end_time ? " - " + b.end_time : "") +
					(actionable ? "" : '<div class="text-muted small">' + b.lesson_date + "</div>") +
					'<div class="text-muted small">' +
					(b.learner_name || "Learner") +
					" · " +
					(b.vehicle_number || b.vehicle || "Vehicle") +
					"</div>" +
					'<span class="badge badge-' + (b.status === "Confirmed" ? "primary" : "warning") + '">' + b.status + "</span>" +
					"</div></div>"
			);

			if (actionable) {
				const $actions = $(
					'<div class="mt-2">' +
						'<button class="btn btn-sm btn-success mr-1" data-action="complete" data-name="' + b.name + '">' + __("Completed") + "</button>" +
						'<button class="btn btn-sm btn-outline-danger" data-action="noshows" data-name="' + b.name + '">' + __("No Show") + "</button>" +
						"</div>"
				);
				$li.append($actions);
			}
			$list.append($li);
		});
	}

	$(document).on("click", '[data-action="complete"], [data-action="noshows"]', (e) => {
		const $btn = $(e.currentTarget);
		const status = $btn.data("action") === "complete" ? "Completed" : "No Show";
		const notes = prompt(__("Instructor notes (optional)"), "");
		if (notes === null) return;

		frappe.call({
			method: "driving_school.api.update_lesson_status",
			args: { lesson_booking: $btn.data("name"), status: status, instructor_notes: notes },
			callback: (r) => {
				if (r.exc) {
					showMsg(r._server_messages ? r._server_messages.join("<br>") : __("Could not update the lesson."), "danger");
					return;
				}
				showMsg(__("Lesson marked as") + " " + status, "success");
				load();
			},
		});
	});

	$("#l-submit").on("click", () => {
		const from = $("#l-from").val();
		const to = $("#l-to").val();
		if (!from || !to) {
			showMsg(__("Please pick both dates."), "warning");
			return;
		}
		frappe.call({
			method: "driving_school.api.request_instructor_leave",
			args: { from_date: from, to_date: to, reason: $("#l-reason").val() },
			callback: (r) => {
				if (r.exc) {
					showMsg(r._server_messages ? r._server_messages.join("<br>") : __("Could not submit leave request."), "danger");
					return;
				}
				showMsg(__("Leave request submitted") + " (" + r.message.name + ").", "success");
				$("#l-reason").val("");
				load();
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
