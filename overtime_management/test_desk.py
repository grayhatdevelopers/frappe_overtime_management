import frappe
from frappe.desk.doctype.sidebar.sidebar import get_sidebar
from frappe.tests import IntegrationTestCase

from overtime_management.patches import replace_app_desk_icon

MODULE = "Overtime Management"


class IntegrationTestDesk(IntegrationTestCase):
	def test_module_has_the_shipped_sidebar(self):
		# Without one, Frappe computes a sidebar from the module's contents.
		sidebar = get_sidebar(MODULE)
		self.assertEqual((sidebar.app, sidebar.standard), ("overtime_management", 1))
		self.assertEqual(
			[item.link_to for item in sidebar.items],
			["Overtime Entry", "Employee Overtime", "Overtime Settings"],
		)

	def test_desk_icon_opens_the_sidebar(self):
		# Icons are imported only on sites using the icon grid, which finds a sidebar by its module.
		icon = frappe.get_file_json(
			frappe.get_app_path("overtime_management", "desktop_icon", "overtime_management.json")
		)
		self.assertEqual((icon["link_type"], icon["link_to"]), ("Workspace Sidebar", MODULE))

	def test_patch_replaces_the_generated_app_icon(self):
		frappe.delete_doc("Desktop Icon", MODULE, force=True)
		frappe.get_doc(
			{
				"doctype": "Desktop Icon",
				"label": MODULE,
				"icon_type": "App",
				"link_type": "External",
				"link": "/app/employee-overtime",
				"app": "overtime_management",
			}
		).insert()

		replace_app_desk_icon.execute()

		icon = frappe.db.get_value("Desktop Icon", MODULE, ["link_type", "link_to", "standard"], as_dict=True)
		self.assertEqual(icon, {"link_type": "Workspace Sidebar", "link_to": MODULE, "standard": 1})
