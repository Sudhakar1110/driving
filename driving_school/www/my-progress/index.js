frappe.ready(() => {
	if (!$("#packages-table").length) return;

	load();

	function load() {
		frappe.call({
			method: "driving_school.api.get_my_progress",
			callback: (r) => {
				if (r.exc) {
					showMsg(
						__("Could not load your progress: ") +
							(r._server_messages ? r._server_messages.join(" ") : __("server error")),
						"danger"
					);
					return;
				}
				render(r.message || {});
			},
			error: () => showMsg(__("Could not load your progress. Please try again."), "danger"),
		});
	}

	const JOURNEY = ["Not Started", "Theory", "Practical", "Test Ready"];
	const STATUS_CLASS = {
		Enquired: "secondary",
		Registered: "info",
		"In Training": "primary",
		"Test Ready": "warning",
		Passed: "success",
		Failed: "danger",
		Dropped: "dark",
	};

	function render(data) {
		const l = data.learner || {};
		$("#pr-name").text(l.learner_name || "—");
		$("#pr-cat").text(l.category || "").toggle(!!l.category);

		const status = l.status || "—";
		$("#pr-status-badge")
			.text(status)
			.removeClass(
				"badge-secondary badge-info badge-primary badge-warning badge-success badge-danger badge-dark"
			)
			.addClass("badge-" + (STATUS_CLASS[status] || "secondary"));
		$("#pr-status").text(status);
		$("#pr-stage").text(l.training_stage || "—");

		renderJourney(l.training_stage, l.status);

		const packages = data.packages || [];
		const totalLessons = packages.reduce((a, p) => a + Number(p.lessons_count || 0), 0);
		const usedLessons = packages.reduce((a, p) => a + Number(p.lessons_used || 0), 0);
		const overallPct = totalLessons ? Math.min(100, Math.round((usedLessons / totalLessons) * 100)) : 0;
		$("#overall-bar")
			.css("width", overallPct + "%")
			.toggleClass("done", totalLessons > 0 && overallPct >= 100);
		$("#overall-text").text(
			totalLessons
				? usedLessons + " / " + totalLessons + " " + __("lessons") + " (" + overallPct + "%)"
				: __("No package yet - book a lesson to get started")
		);
		$("#pr-lessons").text(totalLessons ? usedLessons + " / " + totalLessons : usedLessons);

		const attended = (data.attendance || []).filter((a) => a.status === "Present").length;
		$("#pr-attend").text(attended);

		renderPackages(packages);
		renderMock(data.mock_attempts || []);
		renderTests(data.driving_tests || []);
		renderAttendance(data.attendance || []);
		renderDocuments(data.documents || []);
	}

	function renderJourney(stage, status) {
		const $j = $("#journey").empty();
		const cur = JOURNEY.indexOf(stage || "");
		JOURNEY.forEach((s, i) => {
			const done = status === "Passed" || (cur > -1 && i < cur);
			const active = status !== "Passed" && i === cur;
			const $step = $(
				'<div class="ds-step' + (done ? " done" : "") + (active ? " active" : "") + '">'
			);
			$step.append(
				'<span class="ds-step-dot">' + (done ? "✓" : i + 1) + "</span>" +
					'<span class="ds-step-label">' + __(s) + "</span>"
			);
			$j.append($step);
		});
		$("#journey-label").text(
			status === "Passed"
				? __("Journey complete - well done!")
				: cur > -1
					? __("Currently at:") + " " + __(stage)
					: __("Not started yet")
		);
	}

	function renderPackages(packages) {
		const $pkg = $("#packages-table").empty();
		packages.forEach((p) => {
			const pct = p.lessons_count ? Math.min(100, Math.round((p.lessons_used / p.lessons_count) * 100)) : 0;
			$pkg.append(
				"<tr><td>" +
					"<span class='font-weight-medium'>" + esc(p.package_name) + "</span>" +
					"</td><td>" + esc(p.license_category || "—") + "</td><td>" +
					'<div class="ds-progress small"><div class="ds-progress-bar small" style="width:' + pct + '%"></div></div>' +
					'<span class="small text-muted">' + p.lessons_used + " / " + p.lessons_count + "</span>" +
					"</td><td>" + fmtMoney(p.discounted_amount) + "</td><td>" + fmtMoney(p.balance_amount) +
					"</td><td>" + (p.expiry_date || "—") + "</td><td>" +
					'<span class="badge badge-' + (p.status === "Active" ? "success" : "secondary") + '">' + esc(p.status) + "</span>" +
					"</td></tr>"
			);
		});
		if (!packages.length) {
			$pkg.append(
				'<tr><td colspan="7" class="text-center text-muted py-4">' +
					__("No packages yet. ") +
					'<a href="/book-lesson">' + __("Book a lesson") + "</a>" +
					"</td></tr>"
			);
		}
	}

	function renderMock(attempts) {
		const $mock = $("#mock-table").empty();
		attempts.forEach((m) => {
			$mock.append(
				"<tr><td>" + (m.submitted_at || "").split(" ")[0] + "</td><td>" + esc(m.category) + "</td><td>" +
					m.score_percent + "% (" + m.correct_answers + "/" + m.total_questions + ")</td><td>" +
					'<span class="badge badge-' + (m.result === "Pass" ? "success" : "danger") + '">' + esc(m.result || "—") + "</span>" +
					"</td></tr>"
			);
		});
		if (!attempts.length) {
			$mock.append(
				'<tr><td colspan="4" class="text-center text-muted py-4"><a href="/mock-test">' + __("Take your first mock test") + "</a></td></tr>"
			);
		}
	}

	function renderTests(tests) {
		const $tests = $("#tests-table").empty();
		tests.forEach((t) => {
			const statusClass = t.result === "Pass" ? "success" : t.result === "Fail" ? "danger" : "secondary";
			$tests.append(
				"<tr><td>" + t.test_date + "</td><td>" + esc(t.test_type) + "</td><td>" +
					(t.retake_number || 0) + "</td><td>" + (t.score != null ? t.score + "%" : "—") + "</td><td>" +
					'<span class="badge badge-' + statusClass + '">' + esc(t.result || "Pending") + "</span>" +
					"</td></tr>"
			);
		});
		if (!tests.length) {
			$tests.append('<tr><td colspan="5" class="text-center text-muted py-4">' + __("No tests scheduled yet.") + "</td></tr>");
		}
	}

	function renderAttendance(attendance) {
		const $att = $("#attendance-table").empty();
		attendance.forEach((a) => {
			$att.append(
				"<tr><td>" + a.class_date + "</td><td>" + esc(a.class_title || a.theory_class) + "</td><td>" +
					'<span class="badge badge-' + (a.status === "Present" ? "success" : "danger") + '">' + esc(a.status) + "</span>" +
					"</td></tr>"
			);
		});
		if (!attendance.length) {
			$att.append('<tr><td colspan="3" class="text-center text-muted py-4">' + __("No theory classes attended yet.") + "</td></tr>");
		}
	}

	function renderDocuments(documents) {
		const $docs = $("#documents-table").empty();
		documents.forEach((d) => {
			$docs.append(
				"<tr><td>" + esc(d.doc_type || "—") + "</td><td>" + esc(d.doc_number || "—") + "</td><td>" +
					(d.expiry_date || "—") + "</td><td>" +
					'<span class="badge badge-' + (d.is_verified ? "success" : "warning") + '">' +
					(d.is_verified ? __("Verified") : __("Pending")) + "</span></td></tr>"
			);
		});
		if (!documents.length) {
			$docs.append('<tr><td colspan="4" class="text-center text-muted py-4">' + __("No documents uploaded yet.") + "</td></tr>");
		}
	}

	function esc(v) {
		return String(v == null ? "" : v).replace(/[&<>"']/g, (c) =>
			({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
		);
	}

	function fmtMoney(v) {
		const n = Number(v || 0);
		return n.toLocaleString(undefined, { style: "currency", currency: "USD" });
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
