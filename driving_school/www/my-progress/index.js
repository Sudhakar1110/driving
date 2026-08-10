frappe.ready(() => {
	if (!$("#packages-table").length) return;

	load();

	function load() {
		frappe.call({
			method: "driving_school.api.get_my_progress",
			callback: (r) => {
				if (r.exc) {
					showMsg("Could not load your progress. Please try again.", "danger");
					return;
				}
				render(r.message || {});
			},
		});
	}

	function render(data) {
		const l = data.learner || {};
		$("#pr-status").text(l.status || "—");
		$("#pr-stage").text(l.training_stage || "—");

		let lessonsUsed = 0;
		(data.packages || []).forEach((p) => {
			lessonsUsed += Number(p.lessons_used || 0);
		});
		$("#pr-lessons").text(lessonsUsed);

		const attended = (data.attendance || []).filter((a) => a.status === "Present").length;
		$("#pr-attend").text(attended);

		const $pkg = $("#packages-table").empty();
		(data.packages || []).forEach((p) => {
			$pkg.append(
				"<tr><td>" +
					p.package_name +
					"</td><td>" +
					p.license_category +
					"</td><td>" +
					p.lessons_used +
					" / " +
					p.lessons_count +
					"</td><td>" +
					fmtMoney(p.discounted_amount) +
					"</td><td>" +
					fmtMoney(p.balance_amount) +
					"</td><td>" +
					(p.expiry_date || "—") +
					'</td><td><span class="badge badge-' +
					(p.status === "Active" ? "success" : "secondary") +
					'">' +
					p.status +
					"</span></td></tr>"
			);
		});
		if (!(data.packages || []).length) {
			$pkg.append('<tr><td colspan="7" class="text-center text-muted">' + __("No packages yet.") + "</td></tr>");
		}

		const $mock = $("#mock-table").empty();
		(data.mock_attempts || []).forEach((m) => {
			$mock.append(
				"<tr><td>" +
					(m.submitted_at || "").split(" ")[0] +
					"</td><td>" +
					m.category +
					"</td><td>" +
					m.score_percent +
					"% (" +
					m.correct_answers +
					"/" +
					m.total_questions +
					')</td><td><span class="badge badge-' +
					(m.result === "Pass" ? "success" : "danger") +
					'">' +
					m.result +
					"</span></td></tr>"
			);
		});
		if (!(data.mock_attempts || []).length) {
			$mock.append(
				'<tr><td colspan="4" class="text-center text-muted"><a href="/mock-test">' + __("Take your first mock test") + "</a></td></tr>"
			);
		}

		const $tests = $("#tests-table").empty();
		(data.driving_tests || []).forEach((t) => {
			const statusClass = t.result === "Pass" ? "success" : t.result === "Fail" ? "danger" : "secondary";
			$tests.append(
				"<tr><td>" +
					t.test_date +
					"</td><td>" +
					t.test_type +
					"</td><td>" +
					t.retake_number +
					"</td><td>" +
					(t.score != null ? t.score + "%" : "—") +
					'</td><td><span class="badge badge-' +
					statusClass +
					'">' +
					t.result +
					"</span></td></tr>"
			);
		});
		if (!(data.driving_tests || []).length) {
			$tests.append('<tr><td colspan="5" class="text-center text-muted">' + __("No tests scheduled yet.") + "</td></tr>");
		}

		const $att = $("#attendance-table").empty();
		(data.attendance || []).forEach((a) => {
			$att.append(
				"<tr><td>" +
					a.class_date +
					"</td><td>" +
					(a.class_title || a.theory_class) +
					'</td><td><span class="badge badge-' +
					(a.status === "Present" ? "success" : "danger") +
					'">' +
					a.status +
					"</span></td></tr>"
			);
		});
		if (!(data.attendance || []).length) {
			$att.append('<tr><td colspan="3" class="text-center text-muted">' + __("No theory classes attended yet.") + "</td></tr>");
		}

		const $docs = $("#documents-table").empty();
		(data.documents || []).forEach((d) => {
			$docs.append(
				"<tr><td>" +
					(d.doc_type || "—") +
					"</td><td>" +
					(d.doc_number || "—") +
					"</td><td>" +
					(d.expiry_date || "—") +
					'</td><td><span class="badge badge-' +
					(d.is_verified ? "success" : "warning") +
					'">' +
					(d.is_verified ? __("Verified") : __("Pending")) +
					"</span></td></tr>"
			);
		});
		if (!(data.documents || []).length) {
			$docs.append('<tr><td colspan="4" class="text-center text-muted">' + __("No documents uploaded yet.") + "</td></tr>");
		}
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
