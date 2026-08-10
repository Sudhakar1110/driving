frappe.ready(() => {
	if (!$("#upcoming-list").length) return;

	frappe.call({
		method: "driving_school.api.get_learner_summary",
		callback: (r) => {
			if (r.exc) {
				showMsg("Could not load your dashboard. Please try again.", "danger");
				return;
			}
			render(r.message);
		},
	});

	function render(data) {
		const l = data.learner || {};
		$("#l-name").text(l.learner_name || "—");
		$("#l-status").text(l.status || "—");
		$("#l-stage").text(l.training_stage || "—");
		$("#l-cat-text").text(l.category || "—");
		$("#c-completed").text(data.completed_lessons || 0);
		$("#c-noshows").text(data.no_shows || 0);
		const pkg = data.active_package;
		$("#c-upcoming").text(data.upcoming_count || 0);
		$("#pkg-balance-hero").text(pkg ? fmtMoney(pkg.balance_amount) : "—");

		if (pkg) {
			$("#pkg-block").show();
			$("#pkg-name").text(pkg.package_name);
			$("#pkg-used").text(pkg.lessons_used + " / " + pkg.lessons_count);
			$("#pkg-balance").text(fmtMoney(pkg.balance_amount));
			$("#pkg-expiry").text(pkg.expiry_date || "—");
		} else {
			$("#pkg-none").show();
		}

		if (data.next_test) {
			$("#test-block").show();
			$("#test-info").text(data.next_test.test_type + " on " + data.next_test.test_date);
		}

		const $list = $("#upcoming-list").empty();
		const lessons = data.upcoming_lessons || [];
		if (!lessons.length) {
			$list.append(
				'<li class="list-group-item text-muted">No upcoming lessons. <a href="/book-lesson">Book one now</a>.</li>'
			);
		} else {
			lessons.forEach((b) => {
				$list.append(
					'<li class="list-group-item d-flex justify-content-between align-items-center">' +
						'<span><strong>' +
						b.lesson_date +
						"</strong> at " +
						b.start_time +
						" &middot; " +
						(b.instructor_name || "Instructor") +
						" &middot; " +
						(b.vehicle_number || "Vehicle") +
						"</span>" +
						'<span class="badge ' +
						(b.status === "Confirmed" ? "badge-success" : "badge-warning") +
						'">' +
						b.status +
						"</span></li>"
				);
			});
		}
	}

	function fmtMoney(v) {
		const n = Number(v || 0);
		return n.toLocaleString(undefined, { style: "currency", currency: "USD" });
	}

	function showMsg(msg, type) {
		const types = { danger: "alert-danger", success: "alert-success", warning: "alert-warning", info: "alert-info" };
		$("#ds-msg").html(
			'<div class="alert ' + (types[type] || "alert-info") + ' alert-dismissible fade show" role="alert">' +
				msg +
				'<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>'
		);
	}
});
