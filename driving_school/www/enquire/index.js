frappe.ready(() => {
	if (!$("#e-submit").length) return;

	$("#e-submit").on("click", () => {
		const args = {
			full_name: $("#e-name").val(),
			mobile_number: $("#e-mobile").val(),
			category: $("#e-category").val(),
			email: $("#e-email").val(),
			message: $("#e-message").val(),
		};
		if (!args.full_name || !args.mobile_number) {
			showMsg(__("Please enter your name and mobile number."), "warning");
			return;
		}

		frappe.call({
			method: "driving_school.api.submit_enquiry",
			args: args,
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
