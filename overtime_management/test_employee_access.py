import frappe
from frappe.permissions import has_controller_permissions
from frappe.tests import IntegrationTestCase


class IntegrationTestEmployeeAccess(IntegrationTestCase):
	def test_no_hook_denies_employee_access(self):
		# From Frappe v16 a has_permission hook that returns None denies access.
		employee = frappe.new_doc("Employee")
		for ptype in ("read", "write"):
			self.assertTrue(has_controller_permissions(employee, ptype, user="employee@example.com"), ptype)
