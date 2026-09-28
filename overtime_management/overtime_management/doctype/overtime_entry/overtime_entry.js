frappe.ui.form.on("Overtime Entry", {
	onload: function (frm) {
		// Posting Date defaults to today for a new document
		if (frm.is_new() && !frm.doc.posting_date) {
			frm.set_value("posting_date", frappe.datetime.get_today());
		}

		// Set default frequency if needed
		if (frm.is_new() && !frm.doc.overtime_frequency) {
			frm.set_value("overtime_frequency", "Monthly");
		}

		// Set dates based on frequency
		if (
			frm.is_new() &&
			frm.doc.overtime_frequency &&
			(!frm.doc.start_date || !frm.doc.end_date)
		) {
			set_dates_from_frequency(frm);
		}
	},

	overtime_frequency: function (frm) {
		if (!frm.doc.overtime_frequency) {
			return;
		}

		// Whenever frequency changes, recalculate the period
		set_dates_from_frequency(frm);
	},

	start_date: function (frm) {
		if (!frm.doc.start_date || !frm.doc.overtime_frequency) {
			return;
		}

		// Changing Start Date recalculates End Date
		set_end_date_from_start(frm);
	},

	end_date: function (frm) {
		if (!frm.doc.end_date || !frm.doc.start_date || !frm.doc.overtime_frequency) {
			return;
		}

		validate_date_range(frm);
	},

	refresh: function (frm) {
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Get Employees"), function () {
				if (!frm.doc.company || !frm.doc.start_date || !frm.doc.end_date) {
					frappe.msgprint(__("Please select Company, Start Date, and End Date first"));
					return;
				}

				frappe.call({
					method: "overtime_management.overtime_management.doctype.overtime_entry.overtime_entry.get_matching_employees",
					args: {
						company: frm.doc.company,
						start_date: frm.doc.start_date,
						end_date: frm.doc.end_date,
					},
					callback: function (r) {
						frm.clear_table("employees");

						(r.message || []).forEach((row) => {
							frm.add_child("employees", row);
						});

						frm.refresh_field("employees");

						frappe.msgprint(
							__("Found {0} employee(s) with unclaimed overtime", [
								(r.message || []).length,
							])
						);
					},
				});
			});
		}

		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("View Generated Records"), function () {
				frappe.call({
					method: "overtime_management.overtime_management.doctype.overtime_entry.overtime_entry.get_generated_records",
					args: {
						overtime_entry: frm.doc.name,
					},
					callback: function (r) {
						const records = r.message || [];

						if (!records.length) {
							frappe.msgprint(
								__("No Employee Overtime records found for this entry.")
							);
							return;
						}

						const status_label = {
							0: __("Draft"),
							1: __("Submitted"),
							2: __("Cancelled"),
						};

						const rows = records
							.map(
								(rec) => `
                            <tr>
                                <td>${frappe.utils.escape_html(
									rec.employee_name || rec.employee
								)}</td>
                                <td>
                                    <a href="/app/employee-overtime/${rec.name}" target="_blank">
                                        ${rec.name}
                                    </a>
                                </td>
                                <td>${status_label[rec.docstatus]}</td>
                                <td>${format_currency(rec.ot_amount)}</td>
                            </tr>
                        `
							)
							.join("");

						const html = `
                            <table class="table table-bordered">
                                <thead>
                                    <tr>
                                        <th>${__("Employee")}</th>
                                        <th>${__("Employee Overtime")}</th>
                                        <th>${__("Status")}</th>
                                        <th>${__("OT Amount")}</th>
                                    </tr>
                                </thead>
                                <tbody>${rows}</tbody>
                            </table>
                        `;

						frappe.msgprint({
							title: __("Generated Employee Overtime Records"),
							message: html,
							wide: true,
						});
					},
				});
			});
		}
	},
});

/**
 * Set Start Date and End Date based on the selected frequency.
 *
 * Monthly:
 *   First day of current month -> last day of current month
 *
 * Weekly:
 *   Monday -> Sunday
 *
 * Fortnightly:
 *   Monday -> Sunday of the following week
 */
function set_dates_from_frequency(frm) {
	const today = moment(frappe.datetime.get_today());

	let start_date;
	let end_date;

	switch (frm.doc.overtime_frequency) {
		case "Custom":
			start_date = today.clone().startOf("month");
			end_date = today.clone().endOf("month");
			break;

		case "Monthly":
			start_date = today.clone().startOf("month");
			end_date = today.clone().endOf("month");
			break;

		case "Weekly":
			start_date = today.clone().startOf("isoWeek");
			end_date = today.clone().endOf("isoWeek");
			break;

		case "Fortnightly":
			start_date = today.clone().startOf("isoWeek");
			end_date = start_date.clone().add(13, "days");
			break;

		default:
			return;
	}

	frm.set_value("start_date", start_date.format("YYYY-MM-DD"));
	frm.set_value("end_date", end_date.format("YYYY-MM-DD"));
}

/**
 * When user changes Start Date, calculate the correct End Date.
 */
function set_end_date_from_start(frm) {
	const start = moment(frm.doc.start_date);

	let end;

	switch (frm.doc.overtime_frequency) {
		case "Monthly":
			end = start.clone().add(1, "month").subtract(1, "day");
			break;

		case "Weekly":
			end = start.clone().add(6, "days");
			break;

		case "Fortnightly":
			end = start.clone().add(13, "days");
			break;

		default:
			return;
	}

	frm.set_value("end_date", end.format("YYYY-MM-DD"));
}

/**
 * Validate that the manually selected End Date matches
 * the selected overtime frequency.
 */
function validate_date_range(frm) {
	const start = moment(frm.doc.start_date);
	const end = moment(frm.doc.end_date);

	if (!start.isValid() || !end.isValid()) {
		return;
	}

	let expected_end;

	switch (frm.doc.overtime_frequency) {
		case "Monthly":
			expected_end = start.clone().add(1, "month").subtract(1, "day");
			break;

		case "Weekly":
			expected_end = start.clone().add(6, "days");
			break;

		case "Fortnightly":
			expected_end = start.clone().add(13, "days");
			break;

		default:
			return;
	}

	if (!end.isSame(expected_end, "day")) {
		frappe.msgprint({
			title: __("Invalid Date Range"),
			indicator: "red",
			message: __(
				"For <b>{0}</b> frequency, the End Date must be <b>{1}</b> when the Start Date is <b>{2}</b>.",
				[
					frappe.utils.escape_html(frm.doc.overtime_frequency),
					frappe.datetime.str_to_user(expected_end.format("YYYY-MM-DD")),
					frappe.datetime.str_to_user(start.format("YYYY-MM-DD")),
				]
			),
		});

		// Restore the valid End Date
		frm.set_value("end_date", expected_end.format("YYYY-MM-DD"));
	}
}
