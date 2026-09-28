import frappe
from frappe.model.document import Document
from frappe.utils import add_days, cint, flt, getdate

from overtime_management.permissions import enable_overtime_bypass


class EmployeeOvertime(Document):
	def validate(self):
		enable_overtime_bypass()
		self.validate_overtime_details()
		self.calculate_ot_hours()
		self.fetch_base_salary()
		self.calculate_hourly_rate()
		self.calculate_ot_amount()

	def validate_overtime_details(self):
		if not self.overtime_details:
			frappe.throw("Cannot save: no overtime entries found. Click 'Fetch Overtime Hours' first.")

	def calculate_ot_hours(self):
		self.ot_hours = sum(flt(d.approved_hours) for d in self.overtime_details)

	def fetch_base_salary(self):
		settings = frappe.get_single("Overtime Settings")
		component = settings.salary_component
		if not component:
			frappe.throw("Please configure an OT Basis Salary Component in Overtime Settings")

		ssa = frappe.db.get_value(
			"Salary Structure Assignment",
			{
				"employee": self.employee,
				"docstatus": 1,
				"from_date": ["<=", self.end_date],
			},
			["name", "salary_structure", "base", "from_date"],
			order_by="from_date desc",
			as_dict=True,
		)
		if not ssa:
			frappe.throw(
				f"No Salary Structure Assignment found for {self.employee}. Cannot calculate overtime."
			)

		detail = frappe.db.get_value(
			"Salary Detail",
			{
				"parent": ssa.salary_structure,
				"parentfield": "earnings",
				"salary_component": component,
			},
			["amount", "formula"],
			as_dict=True,
		)
		if not detail:
			frappe.throw(
				f"Salary Structure '{ssa.salary_structure}' assigned to {self.employee} has no "
				f"component '{component}'. Please check Overtime Settings or the employee's Salary Structure."
			)

		if not detail.formula and flt(detail.amount) > 0:
			# flat-amount component
			self.base_salary = flt(detail.amount)
		elif (detail.formula or "").strip() == "base":
			# standard ERPNext pattern: component = base salary directly
			self.base_salary = flt(ssa.base)

	def calculate_hourly_rate(self):
		settings = frappe.get_single("Overtime Settings")
		monthly_hours = flt(settings.standard_working_hours_per_month)
		if monthly_hours <= 0:
			frappe.throw("Please configure Standard Working Hours Per Month in Overtime Settings")
		base_hourly_rate = self.base_salary / monthly_hours
		self.hourly_rate = base_hourly_rate * flt(settings.ot_multiplier)

	def calculate_ot_amount(self):
		self.ot_amount = flt(self.hourly_rate) * flt(self.ot_hours)

	def on_submit(self):
		self.create_additional_salary()

	def create_additional_salary(self):
		existing = frappe.db.exists("Additional Salary", {"ref_docname": self.name, "docstatus": ["!=", 2]})
		if existing:
			frappe.msgprint(f"Additional Salary {existing} already linked to this record.")
			return

		if flt(self.ot_amount) <= 0:
			frappe.msgprint("OT Amount is zero — skipping Additional Salary creation.")
			return

		add_salary = frappe.new_doc("Additional Salary")
		add_salary.employee = self.employee
		add_salary.salary_component = "Overtime"
		add_salary.amount = self.ot_amount
		add_salary.payroll_date = self.end_date
		add_salary.overwrite_salary_structure_amount = 0
		add_salary.ref_doctype = "Employee Overtime"
		add_salary.ref_docname = self.name
		add_salary.insert()
		add_salary.submit()

		frappe.msgprint(f"Additional Salary {add_salary.name} created for {self.employee}")

	def on_cancel(self):
		self.cancel_additional_salary()

	def cancel_additional_salary(self):
		existing = frappe.db.get_value(
			"Additional Salary", {"ref_docname": self.name, "docstatus": 1}, "name"
		)
		if existing:
			add_salary = frappe.get_doc("Additional Salary", existing)
			add_salary.cancel()
			frappe.msgprint(f"Cancelled linked Additional Salary {existing}")


@frappe.whitelist()
def fetch_overtime_from_timesheets(employee, start_date, end_date, current_doc=None):
	start_date = getdate(start_date)
	end_date = getdate(end_date)

	if start_date > end_date:
		frappe.throw("Start Date cannot be after End Date")

	settings = frappe.get_single("Overtime Settings")
	lookback = cint(settings.lookback_days) or 30

	search_start = add_days(start_date, -lookback)
	start_datetime = f"{search_start} 00:00:00"
	end_datetime = f"{add_days(end_date, 1)} 00:00:00"

	ot_rows = frappe.db.sql(
		"""
        SELECT
            td.name AS timesheet_detail,
            td.parent AS timesheet,
            td.from_time,
            td.activity_type,
            td.hours,
            td.project,
            td.task
        FROM `tabTimesheet Detail` td
        INNER JOIN `tabTimesheet` ts
            ON ts.name = td.parent
        WHERE
            ts.employee = %(employee)s
            AND ts.docstatus = 1
            AND td.custom_is_overtime = 1
            AND td.from_time >= %(start_datetime)s
            AND td.from_time < %(end_datetime)s
            AND td.name NOT IN (
                SELECT eod.timesheet_detail
                FROM `tabEmployee Overtime Detail` eod
                INNER JOIN `tabEmployee Overtime` eo ON eo.name = eod.parent
                WHERE eo.docstatus != 2
                    AND eod.timesheet_detail IS NOT NULL
                    AND eod.timesheet_detail != ''
                    AND eo.name != %(current_doc)s
            )
        ORDER BY td.from_time ASC
    """,
		{
			"employee": employee,
			"start_datetime": start_datetime,
			"end_datetime": end_datetime,
			"current_doc": current_doc or "",
		},
		as_dict=True,
	)

	details = []

	for row in ot_rows:
		details.append(
			{
				"timesheet_detail": row.timesheet_detail,
				"timesheet": row.timesheet,
				"date": getdate(row.from_time) if row.from_time else None,
				"activity_type": row.activity_type,
				"hours": row.hours,
				"approved_hours": row.hours,
				"project": row.project,
				"task": row.task,
				"is_prior_period": 1 if getdate(row.from_time) < start_date else 0,
			}
		)

	return details
