frappe.ready(() => {
	const $form = $("#reg-form");
	if (!$form.length) return;

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

	function setLoading(loading) {
		$("#r-submit").prop("disabled", loading);
		$("#r-submit .ds-btn-label").toggle(!loading);
		$("#r-submit .ds-btn-spinner").toggle(loading);
	}

	function validate() {
		const email = $("#r-email").val().trim();
		if (!$("#r-name").val().trim()) return __("Please enter your full name.");
		if (!/^[0-9+()\- ]{7,15}$/.test($("#r-mobile").val().trim()))
			return __("Please enter a valid mobile number.");
		if (!email || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email))
			return __("Please enter a valid email address.");

		const password = $("#r-password").val() || "";
		if (password && password.length < 6)
			return __("Password must be at least 6 characters long.");
		if (password && password !== $("#r-password2").val())
			return __("Passwords do not match.");
		return null;
	}

	$form.on("submit", (e) => {
		e.preventDefault();

		const error = validate();
		if (error) {
			showMsg(error, "warning");
			return;
		}

		const args = {
			full_name: $("#r-name").val().trim(),
			mobile_number: $("#r-mobile").val().trim(),
			email: $("#r-email").val().trim(),
			category: $("#r-category").val(),
			city: $("#r-city").val().trim(),
			address: $("#r-address").val().trim(),
			password: $("#r-password").val() || null,
		};

		setLoading(true);
		frappe.call({
			method: "driving_school.api.register_learner",
			args: args,
			always: () => setLoading(false),
			callback: (r) => {
				if (r.exc) {
					showMsg(
						r._server_messages ? r._server_messages.join("<br>") : __("Registration failed. Please try again."),
						"danger"
					);
					return;
				}
				if (r.message && r.message.logged_in) {
					// Auto-logged in - go straight to the learner portal.
					window.location.href = "/portal-home";
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
});
