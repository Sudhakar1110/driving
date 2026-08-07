// Copyright (c) 2024, Driving School and contributors
// For license information, please see license.txt

frappe.ui.form.on("Enquiry", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.status !== "Registered") {
			frm.add_custom_button(__("Convert to Learner"), () => {
				frm.call("convert_to_learner").then((r) => {
					if (r.message) {
						frappe.show_alert({
							message: __("Learner created: {0}", [r.message]),
							indicator: "green",
						});
						frm.refresh();
					}
				});
			});
		}
	},
});
