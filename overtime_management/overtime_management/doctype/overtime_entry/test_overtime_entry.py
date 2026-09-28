# Copyright (c) 2026, Grayhat and Contributors
# See LICENSE

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import UnitTestCase
from frappe.tests.classes.context_managers import set_user
from frappe.utils import getdate

from overtime_management.overtime_management.doctype.overtime_entry.overtime_entry import (
	OvertimeEntry,
	get_generated_records,
	get_matching_employees,
)


class UnitTestOvertimeEntry(UnitTestCase):
	def make_entry(self, frequency="Weekly", start_date="2026-09-01", end_date="2026-09-07"):
		return OvertimeEntry(
			{
				"doctype": "Overtime Entry",
				"overtime_frequency": frequency,
				"start_date": start_date,
				"end_date": end_date,
			}
		)

	def test_valid_date_ranges(self):
		valid_ranges = (
			("Weekly", "2026-09-01", "2026-09-07"),
			("Fortnightly", "2026-09-01", "2026-09-14"),
			("Monthly", "2026-02-01", "2026-02-28"),
			("Monthly", "2024-02-01", "2024-02-29"),
			("Custom", "2026-09-03", "2026-10-19"),
		)

		for frequency, start_date, end_date in valid_ranges:
			with self.subTest(frequency=frequency, start_date=start_date):
				self.make_entry(frequency, start_date, end_date).validate_date_range()

	def test_end_date_cannot_precede_start_date(self):
		with self.assertRaisesRegex(frappe.ValidationError, "End Date cannot be before Start Date"):
			self.make_entry("Custom", "2026-09-02", "2026-09-01").validate_date_range()

	def test_frequency_requires_exact_end_date(self):
		with self.assertRaisesRegex(frappe.ValidationError, "End Date must be 2026-09-07"):
			self.make_entry("Weekly", "2026-09-01", "2026-09-08").validate_date_range()

	def test_unknown_frequency_is_rejected(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Invalid Overtime Frequency"):
			self.make_entry("Quarterly", "2026-09-01", "2026-09-07").validate_date_range()

	@patch("overtime_management.overtime_management.doctype.overtime_entry.overtime_entry.frappe.get_single")
	@patch("overtime_management.overtime_management.doctype.overtime_entry.overtime_entry.frappe.db.sql")
	def test_get_matching_employees_uses_lookback_and_company_filter(self, sql, get_single):
		get_single.return_value = frappe._dict(lookback_days=15)
		sql.return_value = [frappe._dict(employee="HR-EMP-0001", ot_hours_found=4)]

		rows = get_matching_employees("Acme", "2026-09-16", "2026-09-30")

		self.assertEqual(rows[0].employee, "HR-EMP-0001")
		query, values = sql.call_args.args
		self.assertIn("e.company = %(company)s", query)
		self.assertEqual(values["company"], "Acme")
		self.assertEqual(values["start_datetime"], "2026-09-01 00:00:00")
		self.assertEqual(values["end_datetime"], "2026-10-01 00:00:00")
		self.assertTrue(sql.call_args.kwargs["as_dict"])

	@patch("overtime_management.overtime_management.doctype.overtime_entry.overtime_entry.frappe.get_list")
	def test_get_generated_records_returns_linked_documents(self, get_list):
		get_list.return_value = [{"name": "OTM-EMP-00001", "employee": "HR-EMP-0001"}]

		rows = get_generated_records("OTM-ENT-00001")

		self.assertEqual(rows, get_list.return_value)
		get_list.assert_called_once_with(
			"Employee Overtime",
			filters={"overtime_entry": "OTM-ENT-00001"},
			fields=["name", "employee", "employee_name", "docstatus", "ot_amount"],
		)

	def test_apis_refuse_users_without_overtime_access(self):
		with set_user("Guest"):
			with self.assertRaises(frappe.PermissionError):
				get_matching_employees("Acme", "2026-09-16", "2026-09-30")
			with self.assertRaises(frappe.PermissionError):
				get_generated_records("OTM-ENT-00001")

	def test_create_draft_records_populates_source_details(self):
		entry = self.make_entry()
		entry.name = "OTM-ENT-00001"
		entry.posting_date = getdate("2026-09-08")
		entry.employees = [frappe._dict(employee="HR-EMP-0001")]
		draft = MagicMock()
		draft.name = "OTM-EMP-00001"

		with (
			patch(
				"overtime_management.overtime_management.doctype.overtime_entry.overtime_entry.frappe.new_doc",
				return_value=draft,
			) as new_doc,
			patch(
				"overtime_management.overtime_management.doctype.overtime_entry.overtime_entry.frappe.db.sql",
				return_value=[],
			),
			patch(
				"overtime_management.overtime_management.doctype.employee_overtime.employee_overtime.get_unclaimed_overtime",
				return_value=[{"timesheet_detail": "detail-1", "approved_hours": 2}],
			) as fetch_overtime,
		):
			entry.create_draft_overtime_records()

		new_doc.assert_called_once_with("Employee Overtime")
		fetch_overtime.assert_called_once_with("HR-EMP-0001", entry.start_date, entry.end_date)
		draft.append.assert_called_once_with("overtime_details", fetch_overtime.return_value[0])
		draft.insert.assert_called_once_with()

	def test_create_draft_records_skips_overlapping_submission(self):
		entry = self.make_entry()
		entry.employees = [frappe._dict(employee="HR-EMP-0001")]

		with (
			patch(
				"overtime_management.overtime_management.doctype.overtime_entry.overtime_entry.frappe.new_doc"
			) as new_doc,
			patch(
				"overtime_management.overtime_management.doctype.overtime_entry.overtime_entry.frappe.db.sql",
				return_value=[frappe._dict(name="OTM-EMP-00009")],
			),
		):
			entry.create_draft_overtime_records()

		new_doc.assert_not_called()
