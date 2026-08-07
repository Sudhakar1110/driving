frappe.ready(() => {
	if (!$("#start-btn").length) return;

	let questions = [];

	$("#start-btn").on("click", () => {
		const category = $("#category").val();
		frappe.call({
			method: "driving_school.api.get_mock_questions",
			args: { category: category, count: 10 },
			callback: (r) => {
				if (r.exc) {
					showMsg(__("Could not load questions. Please try again."), "danger");
					return;
				}
				questions = r.message || [];
				if (!questions.length) {
					showMsg(__("No questions available for this category yet. Please check back later."), "warning");
					return;
				}
				renderQuiz();
			},
		});
	});

	function renderQuiz() {
		$("#setup-card").hide();
		$("#result-card").hide();
		$("#quiz-wrap").show();
		$("#quiz-answers").empty();
		$("#ds-msg").empty();

		questions.forEach((q, i) => {
			const $card = $('<div class="card ds-card mb-3"></div>');
			const $body = $('<div class="card-body"></div>');
			$body.append(
				'<p class="mb-2"><strong>' + __("Question") + " " + (i + 1) + ".</strong> " + q.question + "</p>"
			);
			["A", "B", "C", "D"].forEach((opt) => {
				const text = q["option_" + opt.toLowerCase()];
				if (!text) return;
				$body.append(
					'<div class="form-check">' +
						'<input class="form-check-input" type="radio" name="q' +
						q.name +
						'" value="' +
						opt +
						'" id="q' +
						q.name +
						opt +
						'">' +
						'<label class="form-check-label" for="q' +
						q.name +
						opt +
						'">' +
						opt +
						". " +
						text +
						"</label></div>"
				);
			});
			$card.append($body);
			$("#quiz-answers").append($card);
		});

		$("html, body").animate({ scrollTop: 0 }, 300);
	}

	$("#submit-btn").on("click", () => {
		const answers = [];
		questions.forEach((q) => {
			const selected = $('input[name="q' + q.name + '"]:checked').val();
			if (selected) answers.push({ question: q.name, selected_answer: selected });
		});

		if (answers.length < questions.length) {
			showMsg(__("Please answer all questions before submitting."), "warning");
			return;
		}

		$("#submit-btn").prop("disabled", true).text(__("Submitting..."));

		let timedOut = false;
		const timer = setTimeout(() => {
			timedOut = true;
			$("#submit-btn").prop("disabled", false).text(__("Submit Test"));
			showMsg(__("The server took too long to respond. Please try again."), "danger");
		}, 25000);

		frappe.call({
			method: "driving_school.api.submit_mock_test",
			args: { category: $("#category").val(), answers: answers },
			callback: (r) => {
				clearTimeout(timer);
				if (timedOut) return;
				$("#submit-btn").prop("disabled", false).text(__("Submit Test"));
				if (r.exc || !r.message) {
					showMsg(getErrorMsg(r), "danger");
					return;
				}
				renderResults(r.message);
			},
		});
	});

	function getErrorMsg(r) {
		let msg = __("Submission failed. Please try again.");
		try {
			const exc = typeof r.exc === "string" ? JSON.parse(r.exc) : {};
			if (exc._server_messages && exc._server_messages.length) {
				msg = exc._server_messages[0].replace(/<[^>]*>/g, "");
			} else if (exc.exception) {
				msg = String(exc.exception).replace(/^.*?(Error|Exception):\s*/, "");
			}
		} catch (e) {}
		return msg;
	}

	function renderResults(res) {
		const passed = String(res.result || "").toLowerCase().indexOf("pass") !== -1;

		$("#quiz-wrap").hide();
		$("#result-card").show();

		$("#res-score").text(res.score_percent + "%");
		$("#res-verdict")
			.removeClass("text-success text-danger")
			.addClass(passed ? "text-success" : "text-danger")
			.html(passed ? "🎉 " + __("Qualified - You passed the test!") : __("Not Qualified - Better luck next time"));
		$("#res-detail").text(
			__("You answered") + " " + res.correct_answers + " / " + res.total_questions + " " + __("correctly")
		);
		$("#res-passmark").text(__("Pass mark") + ": " + (res.pass_percentage || 60) + "%");

		const list = res.answers || [];
		let html = "";
		if (list.length) {
			html =
				'<div class="card ds-card text-left mt-4"><div class="card-header bg-white"><strong>' +
				__("Answer Review") +
				"</strong></div><ul class='list-group list-group-flush'>";
			list.forEach((a, i) => {
				const ok = a.is_correct == 1 || a.is_correct === true;
				html +=
					"<li class='list-group-item'>" +
					"<span class='mr-2'>" +
					(ok ? "✅" : "❌") +
					"</span><strong>" +
					(i + 1) +
					".</strong> " +
					(a.question || "") +
					"<br><span class='ml-4 text-muted'>" +
					__("Your answer") +
					": " +
					(a.selected_answer || "—") +
					"</span>";
				if (!ok) {
					html +=
						"<br><span class='ml-4 text-danger'>" +
						__("Correct answer") +
						": " +
						(a.correct_answer || "—") +
						"</span>";
				}
				html += "</li>";
			});
			html += "</ul></div>";
		}
		$("#result-review").html(html);
		$("html, body").animate({ scrollTop: 0 }, 300);
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
