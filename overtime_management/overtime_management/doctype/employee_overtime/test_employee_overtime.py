# Copyright (c) 2026, Grayhat and Contributors
# See LICENSE

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import UnitTestCase
from frappe.tests.classes.context_managers import set_user
from frappe.utils import getdate

from overtime_management.overtime_management.doctype.employee_overtime.employee_overtime import (
	EmployeeOvertime,
	fetch_overtime_from_timesheets,
	get_unclaimed_overtime,
)

MODULE = "overtime_management.overtime_management.doctype.employee_overtime.employee_overtime"


class UnitTestEmployeeOvertime(UnitTestCase):
	def make_employee_overtime(self):
		return EmployeeOvertime(
			{
				"doctype": "Employee Overtime",
				"employee": "HR-EMP-0001",
				"start_date": "2026-09-01",
				"end_date": "2026-09-30",
				"overtime_details": [
					{"approved_hours": 2.5},
					{"approved_hours": 1.5},
				],
			}
		)

	def test_calculates_hours_rate_and_amount(self):
		doc = self.make_employee_overtime()
		doc.base_salary = 1600

		with patch(
			"overtime_management.overtime_management.doctype.employee_overtime.employee_overtime.frappe.get_single",
			return_value=frappe._dict(standard_working_hours_per_month=160, ot_multiplier=1.5),
		):
			doc.calculate_ot_hours()
			doc.calculate_hourly_rate()
			doc.calculate_ot_amount()

		self.assertEqual(doc.ot_hours, 4)
		self.assertEqual(doc.hourly_rate, 15)
		self.assertEqual(doc.ot_amount, 60)

	def test_requires_overtime_details(self):
		doc = self.make_employee_overtime()
		doc.overtime_details = []

		with self.assertRaisesRegex(frappe.ValidationError, "no overtime entries found"):
			doc.validate_overtime_details()

	def test_rejects_zero_standard_working_hours(self):
		doc = self.make_employee_overtime()
		doc.base_salary = 1000

		with (
			patch(
				"overtime_management.overtime_management.doctype.employee_overtime.employee_overtime.frappe.get_single",
				return_value=frappe._dict(standard_working_hours_per_month=0, ot_multiplier=1.5),
			),
			self.assertRaisesRegex(frappe.ValidationError, "Standard Working Hours Per Month"),
		):
			doc.calculate_hourly_rate()

	def fetch_base_salary(self, component, ssa=None, date_of_joining="2020-01-01"):
		"""Run fetch_base_salary against one assignment and one structure row;
		return the document and the Salary Structure Assignment filters it used."""
		ssa = (
			ssa
			if ssa is not None
			else frappe._dict(salary_structure="Standard Staff", base=150000, variable=0)
		)
		employee = frappe.get_doc(
			{"doctype": "Employee", "name": "HR-EMP-0001", "date_of_joining": date_of_joining}
		)
		ssa_filters = {}
		db_get_value = frappe.db.get_value

		def get_value(doctype, filters=None, *args, **kwargs):
			if doctype == "Salary Structure Assignment":
				ssa_filters.update(filters)
				return ssa
			if doctype == "Salary Detail":
				return frappe._dict(component)
			return db_get_value(doctype, filters, *args, **kwargs)

		doc = self.make_employee_overtime()
		with (
			patch(f"{MODULE}.frappe.get_single", return_value=frappe._dict(salary_component="Basic")),
			patch(f"{MODULE}.frappe.get_cached_doc", return_value=employee),
			patch(f"{MODULE}.frappe.db.get_value", side_effect=get_value),
		):
			doc.fetch_base_salary()
		return doc, ssa_filters

	def test_base_salary_from_fixed_component(self):
		doc, _ = self.fetch_base_salary({"amount": 42000, "amount_based_on_formula": 0})
		self.assertEqual(doc.base_salary, 42000)

	def test_base_salary_from_base_formula(self):
		doc, _ = self.fetch_base_salary({"amount_based_on_formula": 1, "formula": "base"})
		self.assertEqual(doc.base_salary, 150000)

	def test_base_salary_evaluates_formulas_on_the_assignment(self):
		doc, _ = self.fetch_base_salary({"amount_based_on_formula": 1, "formula": "base * 0.8"})
		self.assertEqual(doc.base_salary, 120000)

	def test_base_salary_uses_the_assignment_in_effect_at_period_start(self):
		_, filters = self.fetch_base_salary({"amount_based_on_formula": 1, "formula": "base"})
		self.assertEqual(filters["from_date"], ["<=", getdate("2026-09-01")])

	def test_base_salary_uses_joining_date_for_mid_period_joiners(self):
		_, filters = self.fetch_base_salary(
			{"amount_based_on_formula": 1, "formula": "base"}, date_of_joining="2026-09-10"
		)
		self.assertEqual(filters["from_date"], ["<=", getdate("2026-09-10")])

	def test_base_salary_rejects_formulas_on_other_components(self):
		with self.assertRaisesRegex(frappe.ValidationError, "uses B, which overtime cannot calculate"):
			self.fetch_base_salary({"amount_based_on_formula": 1, "formula": "B * 0.5"})

	def test_base_salary_rejects_a_component_that_does_not_apply(self):
		with self.assertRaisesRegex(frappe.ValidationError, "comes to zero"):
			self.fetch_base_salary(
				{"amount_based_on_formula": 1, "formula": "base", "condition": "base > 200000"}
			)

	def test_base_salary_requires_an_assignment(self):
		with self.assertRaisesRegex(frappe.ValidationError, "No Salary Structure Assignment"):
			self.fetch_base_salary({"amount_based_on_formula": 1, "formula": "base"}, ssa=frappe._dict())

	@patch(
		"overtime_management.overtime_management.doctype.employee_overtime.employee_overtime.frappe.new_doc"
	)
	@patch(
		"overtime_management.overtime_management.doctype.employee_overtime.employee_overtime.frappe.db.exists"
	)
	def test_submit_creates_and_submits_additional_salary(self, exists, new_doc):
		exists.return_value = None
		additional_salary = MagicMock()
		new_doc.return_value = additional_salary
		doc = self.make_employee_overtime()
		doc.name = "OTM-EMP-00001"
		doc.ot_amount = 60

		doc.create_additional_salary()

		self.assertEqual(additional_salary.employee, doc.employee)
		self.assertEqual(additional_salary.salary_component, "Overtime")
		self.assertEqual(additional_salary.amount, 60)
		self.assertEqual(additional_salary.ref_docname, doc.name)
		additional_salary.insert.assert_called_once_with()
		additional_salary.submit.assert_called_once_with()

	@patch(
		"overtime_management.overtime_management.doctype.employee_overtime.employee_overtime.frappe.new_doc"
	)
	@patch(
		"overtime_management.overtime_management.doctype.employee_overtime.employee_overtime.frappe.db.exists"
	)
	def test_additional_salary_is_idempotent(self, exists, new_doc):
		exists.return_value = "HR-ADS-00001"
		doc = self.make_employee_overtime()
		doc.name = "OTM-EMP-00001"
		doc.ot_amount = 60

		doc.create_additional_salary()

		new_doc.assert_not_called()

	@patch(
		"overtime_management.overtime_management.doctype.employee_overtime.employee_overtime.frappe.get_doc"
	)
	@patch(
		"overtime_management.overtime_management.doctype.employee_overtime.employee_overtime.frappe.db.get_value"
	)
	def test_cancel_cancels_linked_additional_salary(self, get_value, get_doc):
		get_value.return_value = "HR-ADS-00001"

		self.make_employee_overtime().cancel_additional_salary()

		get_doc.assert_called_once_with("Additional Salary", "HR-ADS-00001")
		get_doc.return_value.cancel.assert_called_once_with()

	@patch(
		"overtime_management.overtime_management.doctype.employee_overtime.employee_overtime.frappe.get_single"
	)
	@patch(
		"overtime_management.overtime_management.doctype.employee_overtime.employee_overtime.frappe.db.sql"
	)
	def test_fetch_timesheets_maps_rows_and_marks_prior_period(self, sql, get_single):
		get_single.return_value = frappe._dict(lookback_days=10)
		sql.return_value = [
			frappe._dict(
				timesheet_detail="detail-1",
				timesheet="TS-1",
				from_time="2026-08-30 09:00:00",
				activity_type="Execution",
				hours=2,
				project="PROJ-1",
				task=None,
			)
		]

		rows = get_unclaimed_overtime("HR-EMP-0001", "2026-09-01", "2026-09-30")

		self.assertEqual(rows[0]["approved_hours"], 2)
		self.assertEqual(rows[0]["is_prior_period"], 1)
		query, values = sql.call_args.args
		self.assertIn("ts.docstatus = 1", query)
		self.assertIn("td.custom_is_overtime = 1", query)
		self.assertEqual(values["start_datetime"], "2026-08-22 00:00:00")
		self.assertEqual(values["end_datetime"], "2026-10-01 00:00:00")

	def test_fetch_timesheets_refuses_users_without_overtime_access(self):
		with set_user("Guest"), self.assertRaises(frappe.PermissionError):
			fetch_overtime_from_timesheets("HR-EMP-0001", "2026-09-01", "2026-09-30")

	def test_fetch_timesheets_rejects_reversed_period(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Start Date cannot be after End Date"):
			fetch_overtime_from_timesheets("HR-EMP-0001", "2026-09-30", "2026-09-01")
