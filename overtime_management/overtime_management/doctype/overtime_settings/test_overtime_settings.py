# Copyright (c) 2026, Grayhat and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase


class IntegrationTestOvertimeSettings(IntegrationTestCase):
	def test_settings_doctype_is_single_and_has_required_calculation_fields(self):
		meta = frappe.get_meta("Overtime Settings")

		self.assertTrue(meta.issingle)
		for fieldname in ("salary_component", "standard_working_hours_per_month", "ot_multiplier"):
			self.assertTrue(meta.get_field(fieldname).reqd, f"{fieldname} must be required")

	def test_settings_defaults_are_safe(self):
		meta = frappe.get_meta("Overtime Settings")

		self.assertEqual(float(meta.get_field("standard_working_hours_per_month").default), 160)
		self.assertEqual(float(meta.get_field("ot_multiplier").default), 1)
		self.assertEqual(int(meta.get_field("lookback_days").default), 30)
