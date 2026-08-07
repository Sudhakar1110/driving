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

		frappe.call({
			method: "driving_school.api.submit_mock_test",
			args: { category: $("#category").val(), answers: answers },
			callback: (r) => {
				if (r.exc) {
					showMsg(__("Submission failed. Please try again."), "danger");
					return;
				}
				const res = r.message;
				$("#quiz-wrap").hide();
				$("#result-card").show();
				$("#res-score").text(res.score_percent + "%");
				$("#res-detail").text(
					__("You answered") + " " + res.correct_answers + " / " + res.total_questions + " " + __("correctly")
				);
				$("#res-badge")
					.text(res.result)
					.attr("class", "badge badge-" + (res.result === "Pass" ? "success" : "danger"));
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
