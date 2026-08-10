frappe.ready(() => {
	if (!$("#theory-table").length) return;

	frappe.call({
		method: "driving_school.api.get_class_schedules",
		args: { days: 7 },
		callback: (r) => {
			if (r.exc) {
				showMsg(__("Could not load the schedules. Please try again."), "danger");
				return;
			}
			render(r.message || {});
		},
	});

	function render(data) {
		const $theory = $("#theory-table").empty();
		const classes = data.theory_classes || [];
		if (!classes.length) {
			$theory.append(
				'<tr><td colspan="6" class="text-muted text-center">' + __("No theory classes scheduled in the next 7 days.") + "</td></tr>"
			);
		} else {
			classes.forEach((c) => {
				$theory.append(
					"<tr>" +
						"<td>" + c.class_date + "</td>" +
						"<td>" + (c.start_time ? c.start_time.slice(0, 5) : "—") +
							(c.end_time ? " - " + c.end_time.slice(0, 5) : "") + "</td>" +
						"<td><strong>" + c.title + "</strong></td>" +
						"<td>" + (c.instructor_name || "—") + "</td>" +
						"<td>" + (c.venue || "—") + "</td>" +
						"<td>" + (c.branch_name || "—") + "</td>" +
						"</tr>"
				);
			});
		}

		const $avail = $("#availability").empty();
		const days = data.days || [];
		if (!days.length) {
			$avail.append('<p class="text-muted mb-0">' + __("No availability to show.") + "</p>");
			return;
		}

		days.forEach((d) => {
			const isToday = d.date === frappe.datetime.get_today();
			const open = d.slots.filter((s) => s.available).length;
			const $card = $(
				'<div class="card ds-card mb-3"><div class="card-body py-3">' +
					'<div class="d-flex justify-content-between align-items-center flex-wrap mb-2">' +
						"<strong>" +
						(isToday ? __("Today") + " - " : "") +
						d.date +
						"</strong>" +
						'<span class="small text-muted">' +
						(open ? open + " " + __("slots open") : __("fully booked")) +
						"</span>" +
					"</div>" +
					'<div class="d-flex flex-wrap">' +
						d.slots.map((s) => slotChip(s, d.date)).join("") +
					"</div>" +
				"</div></div>"
			);
			$avail.append($card);
		});
	}

	function slotChip(s, date) {
		if (s.available) {
			return (
				'<a class="btn btn-sm btn-outline-success ds-slot" href="/book-lesson?date=' +
				date +
				'">' +
				s.start_time.slice(0, 5) +
				"</a>"
			);
		}
		return '<span class="btn btn-sm btn-light text-muted ds-disabled ds-slot">' + s.start_time.slice(0, 5) + "</span>";
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
});
