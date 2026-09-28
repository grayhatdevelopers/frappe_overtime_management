frappe.ui.form.on("Employee Overtime", {
	onload: function (frm) {
		if (!frm.is_new()) {
			return;
		}

		if (!frm.doc.posting_date) {
			frm.set_value("posting_date", frappe.datetime.get_today());
		}

		if (!frm.doc.start_date) {
			frm.set_value("start_date", frappe.datetime.get_today());
		}

		if (!frm.doc.end_date) {
			frm.set_value("end_date", frappe.datetime.add_days(frappe.datetime.get_today(), 30));
		}
	},

	refresh: function (frm) {
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Fetch Overtime Hours"), function () {
				if (!frm.doc.employee || !frm.doc.start_date || !frm.doc.end_date) {
					frappe.msgprint(__("Please select Employee and Period first"));
					return;
				}

				frappe.call({
					method: "overtime_management.overtime_management.doctype.employee_overtime.employee_overtime.fetch_overtime_from_timesheets",
					args: {
						employee: frm.doc.employee,
						start_date: frm.doc.start_date,
						end_date: frm.doc.end_date,
						current_doc: frm.doc.name,
					},
					callback: function (r) {
						frm.clear_table("overtime_details");
						(r.message || []).forEach((row) => frm.add_child("overtime_details", row));
						frm.refresh_field("overtime_details");
						frappe.msgprint(
							__("Fetched {0} overtime entries", [(r.message || []).length])
						);
					},
				});
			});
		}
	},
});
