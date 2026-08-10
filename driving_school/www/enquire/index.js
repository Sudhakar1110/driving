frappe.ready(() => {
	const $form = $("#enquire-form");
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
		$("#e-submit").prop("disabled", loading);
		$("#e-submit .ds-btn-label").toggle(!loading);
		$("#e-submit .ds-btn-spinner").toggle(loading);
	}

	$form.on("submit", (e) => {
		e.preventDefault();

		if (!$("#e-name").val().trim()) {
			showMsg(__("Please enter your name."), "warning");
			return;
		}
		if (!/^[0-9+()\- ]{7,15}$/.test($("#e-mobile").val().trim())) {
			showMsg(__("Please enter a valid mobile number."), "warning");
			return;
		}
		const email = $("#e-email").val().trim();
		if (email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
			showMsg(__("Please enter a valid email address."), "warning");
			return;
		}

		const args = {
			full_name: $("#e-name").val().trim(),
			mobile_number: $("#e-mobile").val().trim(),
			category: $("#e-category").val(),
			email: email,
			message: $("#e-message").val().trim(),
		};

		setLoading(true);
		frappe.call({
			method: "driving_school.api.submit_enquiry",
			args: args,
			always: () => setLoading(false),
			callback: (r) => {
				if (r.exc) {
					showMsg(
						r._server_messages ? r._server_messages.join("<br>") : __("Could not submit your enquiry."),
						"danger"
					);
					return;
				}
				$("#enquire-form").hide();
				$("#enquire-done").show();
				$("#e-done-ref").text(__("Thank you! Reference") + ": " + r.message.name);
			},
		});
	});
});
