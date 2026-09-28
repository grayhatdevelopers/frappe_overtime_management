import datetime

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, add_months, cint, flt, getdate

from overtime_management.permissions import enable_overtime_bypass


class OvertimeEntry(Document):
	def validate(self):
		enable_overtime_bypass()
		if not self.posting_date:
			self.posting_date = frappe.utils.getdate()

		if not self.overtime_frequency:
			frappe.throw(_("Please select Overtime Frequency."))

		if not self.start_date or not self.end_date:
			frappe.throw(_("Please select Start Date and End Date."))

		self.validate_date_range()

		if not self.employees:
			frappe.throw(_("Cannot save: no employees found. Click 'Get Employees' first."))

	def validate_date_range(self):
		start_date = getdate(self.start_date)
		end_date = getdate(self.end_date)
		frequency = (self.overtime_frequency or "").strip().lower()

		if end_date < start_date:
			frappe.throw(_("End Date cannot be before Start Date."))

		if frequency == "custom":
			return

		if frequency == "monthly":
			expected_end = add_days(add_months(start_date, 1), -1)

		elif frequency == "weekly":
			expected_end = add_days(start_date, 6)

		elif frequency == "fortnightly":
			expected_end = add_days(start_date, 13)

		else:
			frappe.throw(_("Invalid Overtime Frequency: {0}").format(self.overtime_frequency))

		if end_date != expected_end:
			frappe.throw(
				_("For {0} frequency, the End Date must be {1} when the Start Date is {2}.").format(
					self.overtime_frequency, expected_end, start_date
				)
			)

	def on_submit(self):
		if not self.employees:
			frappe.throw(_("No employees found. Click 'Get Employees' before submitting."))

		self.create_draft_overtime_records()

	def create_draft_overtime_records(self):
		created, skipped = [], []

		for row in self.employees:
			overlapping = frappe.db.sql(
				"""
                SELECT name FROM `tabEmployee Overtime`
                WHERE employee = %(employee)s
                    AND docstatus = 1
                    AND start_date <= %(end_date)s
                    AND end_date >= %(start_date)s
            """,
				{"employee": row.employee, "start_date": self.start_date, "end_date": self.end_date},
				as_dict=True,
			)

			if overlapping:
				skipped.append(row.employee)
				continue

			eo = frappe.new_doc("Employee Overtime")
			eo.employee = row.employee
			eo.posting_date = self.posting_date
			eo.start_date = self.start_date
			eo.end_date = self.end_date
			eo.overtime_entry = self.name

			from overtime_management.overtime_management.doctype.employee_overtime.employee_overtime import (
				get_unclaimed_overtime,
			)

			details = get_unclaimed_overtime(row.employee, self.start_date, self.end_date)

			for d in details:
				eo.append("overtime_details", d)

			eo.insert()
			created.append(eo.name)

		frappe.msgprint(
			_(
				"Created {0} draft Employee Overtime record(s). "
				"Skipped {1} (already covered by an existing submitted record)."
			).format(len(created), len(skipped))
		)


@frappe.whitelist()
def get_matching_employees(company: str, start_date: datetime.date, end_date: datetime.date):
	frappe.has_permission("Overtime Entry", "create", throw=True)

	start_date = getdate(start_date)
	end_date = getdate(end_date)

	settings = frappe.get_single("Overtime Settings")
	lookback = cint(settings.lookback_days) or 30
	search_start = add_days(start_date, -lookback)

	start_datetime = f"{search_start} 00:00:00"
	end_datetime = f"{add_days(end_date, 1)} 00:00:00"

	values = {
		"start_datetime": start_datetime,
		"end_datetime": end_datetime,
		"company": company or "",
	}

	rows = frappe.db.sql(
		"""
        SELECT
            e.name AS employee,
            e.employee_name,
            SUM(td.hours) AS ot_hours_found
        FROM `tabEmployee` e
        INNER JOIN `tabTimesheet` ts ON ts.employee = e.name
        INNER JOIN `tabTimesheet Detail` td ON td.parent = ts.name
        WHERE
            e.status = 'Active'
            AND ts.docstatus = 1
            AND td.custom_is_overtime = 1
            AND td.from_time >= %(start_datetime)s
            AND td.from_time < %(end_datetime)s
            AND (%(company)s = '' OR e.company = %(company)s)
            AND td.name NOT IN (
                SELECT eod.timesheet_detail
                FROM `tabEmployee Overtime Detail` eod
                INNER JOIN `tabEmployee Overtime` eo ON eo.name = eod.parent
                WHERE eo.docstatus != 2
                    AND eod.timesheet_detail IS NOT NULL
                    AND eod.timesheet_detail != ''
            )
        GROUP BY e.name
        ORDER BY e.employee_name
    """,
		values,
		as_dict=True,
	)

	return rows


@frappe.whitelist()
def get_generated_records(overtime_entry: str):
	"""Live lookup replacing the old stored employee_overtime back-link.
	Returns {employee: employee_overtime_name} for every Employee Overtime
	that was generated from this Overtime Entry (any status, including cancelled)."""
	# Check the doctype first, so users without access can't probe which entries exist.
	frappe.has_permission("Overtime Entry", "read", throw=True)
	frappe.has_permission("Overtime Entry", "read", doc=overtime_entry, throw=True)
	rows = frappe.get_list(
		"Employee Overtime",
		filters={"overtime_entry": overtime_entry},
		fields=["name", "employee", "employee_name", "docstatus", "ot_amount"],
	)
	return rows
