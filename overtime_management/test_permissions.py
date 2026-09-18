from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from overtime_management.permissions import (
	employee_permission_override,
	enable_overtime_bypass,
	user_may_bypass_employee_restriction,
)


class IntegrationTestOvertimePermissions(UnitTestCase):
	def tearDown(self):
		frappe.flags.pop("overtime_permission_bypass", None)
		super().tearDown()

	@patch("overtime_management.permissions.frappe.get_roles")
	def test_only_overtime_manager_can_bypass_employee_restriction(self, get_roles):
		get_roles.return_value = ["Employee", "Overtime Manager"]
		self.assertTrue(user_may_bypass_employee_restriction("reviewer@example.com"))

		get_roles.return_value = ["Employee"]
		self.assertFalse(user_may_bypass_employee_restriction("employee@example.com"))

	@patch("overtime_management.permissions.frappe.get_roles", return_value=["Overtime Manager"])
	def test_enable_bypass_sets_request_local_flag(self, _get_roles):
		enable_overtime_bypass()

		self.assertTrue(frappe.flags.overtime_permission_bypass)

	@patch("overtime_management.permissions.frappe.get_roles", return_value=["Overtime Manager"])
	def test_override_only_grants_read_with_active_flag(self, _get_roles):
		self.assertIsNone(employee_permission_override(None, "read", "reviewer@example.com"))
		frappe.flags.overtime_permission_bypass = True
		self.assertTrue(employee_permission_override(None, "read", "reviewer@example.com"))
		self.assertIsNone(employee_permission_override(None, "write", "reviewer@example.com"))
