frappe.ready(() => {
	if (!$("#booking-form").length) return;

	const state = { package: null };

	loadSummary();
	loadResources();

	function loadSummary() {
		frappe.call({
			method: "driving_school.api.get_learner_summary",
			callback: (r) => {
				if (r.exc) {
					showMsg("Could not load your account. Please try again.", "danger");
					return;
				}
				const pkg = r.message && r.message.active_package;
				// Booking requires an active package with a fully paid balance -
				// otherwise show the warning banner instead of the booking form.
				if (pkg && Number(pkg.balance_amount || 0) <= 0) {
					state.package = pkg.name;
					$("#pkg-label").text(pkg.package_name);
					$("#booking-form").show();
				} else {
					$("#no-package").show();
				}
			},
		});
	}

	function loadResources() {
		frappe.call({
			method: "driving_school.api.get_resources",
			callback: (r) => {
				if (r.exc) return;
				const res = r.message || {};
				const $ins = $("#instructor").empty().append('<option value="">' + __("Select instructor") + "</option>");
				(res.instructors || []).forEach((i) =>
					$ins.append('<option value="' + i.name + '">' + i.instructor_name + "</option>")
				);
				const $veh = $("#vehicle").empty().append('<option value="">' + __("Select vehicle") + "</option>");
				(res.vehicles || []).forEach((v) =>
					$veh.append(
						'<option value="' +
							v.name +
							'">' +
							v.vehicle_number +
							(v.vehicle_model ? " (" + v.vehicle_model + ")" : "") +
							"</option>"
					)
				);
			},
		});
	}

	// Pre-fill the date when arriving from the class schedules page (?date=YYYY-MM-DD).
	const urlDate = new URLSearchParams(window.location.search).get("date");
	$("#lesson-date")
		.val(urlDate || frappe.datetime.get_today())
		.on("change", loadSlots);
	$("#instructor").on("change", loadSlots);
	$("#vehicle").on("change", loadSlots);
	loadSlots();

	function loadSlots() {
		const date = $("#lesson-date").val();
		if (!date) return;
		frappe.call({
			method: "driving_school.api.get_available_slots",
			args: {
				lesson_date: date,
				instructor: $("#instructor").val() || null,
				vehicle: $("#vehicle").val() || null,
			},
			callback: (r) => {
				if (r.exc) return;
				renderSlots(r.message || []);
			},
		});
	}

	function renderSlots(slots) {
		const $grid = $("#slot-grid").empty();
		if (!slots.length) {
			$grid.append('<span class="text-muted">' + __("No slots available for this date.") + "</span>");
			return;
		}
		slots.forEach((s) => {
			const $btn = $('<button type="button" class="btn btn-sm ds-slot"></button>').text(
				s.start_time + " - " + s.end_time
			);
			if (s.available) {
				$btn.addClass("btn-outline-success").on("click", () => selectSlot($btn, s.start_time));
			} else {
				$btn.addClass("btn-light text-muted ds-disabled");
			}
			$grid.append($btn);
		});
	}

	function selectSlot($btn, time) {
		$("#slot-grid .ds-slot").removeClass("btn-success").addClass("btn-outline-success");
		$btn.removeClass("btn-outline-success").addClass("btn-success");
		$("#selected-time").val(time);
	}

	$("#book-btn").on("click", () => {
		const date = $("#lesson-date").val();
		const time = $("#selected-time").val();
		const instructor = $("#instructor").val();
		const vehicle = $("#vehicle").val();

		if (!date || !time) {
			showMsg(__("Please choose an available time slot."), "warning");
			return;
		}
		if (!instructor || !vehicle) {
			showMsg(__("Please select an instructor and a vehicle."), "warning");
			return;
		}

		frappe.call({
			method: "driving_school.api.book_lesson",
			args: {
				lesson_date: date,
				start_time: time,
				instructor: instructor,
				vehicle: vehicle,
				package: state.package,
			},
			callback: (r) => {
				if (r.exc) {
					showMsg(
						r._server_messages
							? r._server_messages.join("<br>")
							: __("Booking failed. Please check the details."),
						"danger"
					);
					return;
				}
				showMsg(
					__("Lesson booked! Reference") +
						": " +
						r.message.name +
						" (" +
						__("status") +
						": " +
						r.message.status +
						")",
					"success"
				);
				$("#selected-time").val("");
				loadSlots();
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
