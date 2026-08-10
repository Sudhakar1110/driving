frappe.ready(() => {
	if (!$("#r-submit").length) return;

	$("#r-submit").on("click", () => {
		const password = $("#r-password").val();
		const args = {
			full_name: $("#r-name").val(),
			mobile_number: $("#r-mobile").val(),
			email: $("#r-email").val(),
			category: $("#r-category").val(),
			city: $("#r-city").val(),
			address: $("#r-address").val(),
			password: password || null,
		};

		if (!args.full_name || !args.mobile_number || !args.email) {
			showMsg(__("Please fill in your name, mobile number and email."), "warning");
			return;
		}
		if (password && password !== $("#r-password2").val()) {
			showMsg(__("Passwords do not match."), "warning");
			return;
		}

		frappe.call({
			method: "driving_school.api.register_learner",
			args: args,
			callback: (r) => {
				if (r.exc) {
					showMsg(
						r._server_messages ? r._server_messages.join("<br>") : __("Registration failed. Please try again."),
						"danger"
					);
					return;
				}
				$("#reg-form").hide();
				$("#reg-done").show();
				$("#r-done-text").text(
					__("Welcome, {0}! Your learner ID is {1}.").format(r.message.learner_name, r.message.name)
				);
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
