import frappe

# Single source of truth: who can bypass the Employee User Permission
# restriction specifically for the overtime workflow.
OVERTIME_BYPASS_ROLES = frozenset({"Overtime Manager"})


def user_may_bypass_employee_restriction(user=None):
	user = user or frappe.session.user
	return bool(OVERTIME_BYPASS_ROLES.intersection(frappe.get_roles(user)))


def enable_overtime_bypass():
	"""Call at the top of validate() for every doctype in the overtime
	chain. frappe.flags is reset automatically per-request, so this
	never leaks between users or requests."""
	if user_may_bypass_employee_restriction():
		frappe.flags.overtime_permission_bypass = True


def employee_permission_override(doc, ptype, user):
	"""Registered as a has_permission hook for Employee.
	Only grants access when all three hold:
	  1. ptype == 'read'
	  2. the bypass flag is active for this request (set by enable_overtime_bypass)
	  3. the acting user actually holds Overtime Manager
	Everywhere else in the system, returns None and the normal
	User Permission restriction applies unchanged."""
	if ptype != "read":
		return None
	if not frappe.flags.get("overtime_permission_bypass"):
		return None
	if user_may_bypass_employee_restriction(user):
		return True
	return None
