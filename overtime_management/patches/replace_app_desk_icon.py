import os

import frappe
from frappe.modules.import_file import import_file_by_path

ICON = "Overtime Management"


def execute():
	"""Replace the desk icon Frappe v16 made from add_to_apps_screen with the one the app ships.

	The generated icon opens a list without the app's sidebar. Migrate keeps it when it is newer
	than the shipped file, so it is replaced here.
	"""
	if frappe.db.get_value("Desktop Icon", ICON, "standard") == 0:
		frappe.delete_doc("Desktop Icon", ICON, force=True, ignore_permissions=True)
	path = os.path.join(
		frappe.get_app_path("overtime_management"), "desktop_icon", "overtime_management.json"
	)
	import_file_by_path(path, force=True)
