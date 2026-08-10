frappe.ready(() => {
	if (!$("#payment-table").length) return;

	let state = { package: null, balance: 0 };

	load();

	function load() {
		frappe.call({
			method: "driving_school.api.get_my_payments",
			callback: (r) => {
				if (r.exc) {
					showMsg(
						__("Could not load payments: ") +
							(r._server_messages ? r._server_messages.join(" ") : __("server error")),
						"danger"
					);
					return;
				}
				render(r.message || {});
			},
			error: () => showMsg(__("Could not load payments. Please try again."), "danger"),
		});
	}

	function render(data) {
		const pkg = data.active_package;
		state.package = pkg ? pkg.name : null;
		state.balance = pkg ? Number(pkg.balance_amount || 0) : 0;

		$("#p-total-paid").text(fmtMoney(data.total_paid));
		$("#p-balance").text(fmtMoney(state.balance));
		$("#p-pkg").text(pkg ? pkg.package_name : __("None"));

		if (pkg && state.balance > 0) {
			$("#pay-notice")
				.removeClass("alert-info alert-warning alert-success")
				.addClass("alert-info")
				.html(__("Your package has an outstanding balance of ") + "<strong>" + fmtMoney(state.balance) + "</strong>.")
				.show();
			$("#pay-amount").val(state.balance);
			$("#pay-type").val("Package Fee");
		} else if (pkg) {
			$("#pay-notice")
				.removeClass("alert-info alert-warning alert-success")
				.addClass("alert-success")
				.html(__("Your package is fully paid. You can still record a payment (add-on lessons, test fees, etc.)."))
				.show();
			$("#pay-amount").val("");
			$("#pay-type").val("Add-on Lesson");
		} else {
			$("#pay-notice")
				.removeClass("alert-info alert-warning alert-success")
				.addClass("alert-warning")
				.html(__("No active package yet. You can still record a payment (registration fee, add-on lessons, test fees, etc.)."))
				.show();
			$("#pay-amount").val("");
			$("#pay-type").val("Other");
		}

		const $tbody = $("#payment-table").empty();
		const payments = data.payments || [];
		if (!payments.length) {
			$tbody.append('<tr><td colspan="6" class="text-center text-muted">' + __("No payments yet.") + "</td></tr>");
		}
		payments.forEach((p) => {
			const statusClass =
				p.status === "Received" || p.status === "Reconciled"
					? "badge-success"
					: p.status === "Cancelled"
					? "badge-danger"
					: "badge-warning";
			$tbody.append(
				"<tr>" +
					"<td>" +
					p.payment_date +
					"</td><td>" +
					p.payment_type +
					"</td><td>" +
					p.mode_of_payment +
					"</td><td>" +
					(p.reference_number || "—") +
					'</td><td class="text-right">' +
					fmtMoney(p.amount) +
					'</td><td><span class="badge ' +
					statusClass +
					'">' +
					p.status +
					"</span></td></tr>"
			);
		});
	}

	$("#pay-btn").on("click", () => {
		const amount = parseFloat($("#pay-amount").val());
		if (!amount || amount <= 0) {
			showMsg(__("Enter a valid amount."), "warning");
			return;
		}
		frappe.call({
			method: "driving_school.api.request_payment",
			args: {
				package: state.package,
				amount: amount,
				payment_type: $("#pay-type").val(),
				mode_of_payment: $("#pay-mode").val(),
				reference_number: $("#pay-ref").val(),
			},
			callback: (r) => {
				if (r.exc) {
					showMsg(
						r._server_messages ? r._server_messages.join("<br>") : __("Payment request failed."),
						"danger"
					);
					return;
				}
				showMsg(
					__("Payment request submitted") + " (" + r.message.name + "). " + __("The school will confirm it shortly."),
					"success"
				);
				$("#pay-ref").val("");
				load();
			},
			error: () => showMsg(__("Payment request failed. Please try again."), "danger"),
		});
	});

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
