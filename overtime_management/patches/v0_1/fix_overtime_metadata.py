import frappe

DEFAULT_SINGLE_VALUES = {
	"standard_working_hours_per_month": 160,
	"ot_multiplier": 1.0,
	"lookback_days": 30,
}


def execute():
	frappe.reload_doc("overtime_management", "doctype", "overtime_entry", force=True)
	frappe.reload_doc("overtime_management", "doctype", "employee_overtime", force=True)
	frappe.reload_doc("overtime_management", "doctype", "overtime_settings", force=True)

	for fieldname, value in DEFAULT_SINGLE_VALUES.items():
		if frappe.db.get_single_value("Overtime Settings", fieldname) in (None, ""):
			frappe.db.set_single_value("Overtime Settings", fieldname, value)
