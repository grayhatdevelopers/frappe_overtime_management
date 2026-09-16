# Overtime Management

Overtime Management is a Frappe/ERPNext HRMS app for turning approved overtime logged in Timesheets into payroll-ready Additional Salary records.

It gives HR teams a controlled workflow to:

- mark individual Timesheet Detail rows as overtime;
- collect unclaimed overtime for a company and pay period;
- review and adjust approved hours per employee;
- calculate overtime from an employee's assigned salary structure; and
- create or cancel the corresponding Additional Salary automatically.

## How it works

```text
Submitted Timesheet
  -> Timesheet Detail marked "Is Overtime"
  -> Overtime Entry for a pay period
  -> one draft Employee Overtime record per employee
  -> review approved hours and submit
  -> submitted Additional Salary using the "Overtime" component
```

Overtime rows are only eligible when their parent Timesheet is submitted. A Timesheet Detail row already linked to a non-cancelled Employee Overtime record is excluded, which prevents the same time from being claimed twice.

The app can also search before the selected period for previously unreported overtime. These rows are marked **Prior Period** in the Employee Overtime details table.

## Features

- Bulk overtime processing through **Overtime Entry**
- Manual per-employee processing through **Employee Overtime**
- Monthly, fortnightly, weekly, and custom pay periods
- Configurable lookback window for missed overtime
- Editable approved hours and reviewer comments
- Project, task, activity, Timesheet, and source-row traceability
- Configurable salary basis, standard monthly hours, and overtime multiplier
- Automatic Additional Salary creation on submit
- Automatic cancellation of the linked Additional Salary when Employee Overtime is cancelled
- Overlap and duplicate-claim protection
- Dedicated **Overtime Manager** role

## Compatibility

Version `v0.2.0` has been tested with:

| App | Version |
| --- | --- |
| Frappe Framework | Version 16 |
| ERPNext | `v16.28.0` |
| HRMS | `v16.7.1` |

Payments `version-16` and Frappe Assistant Core `v2.5.0` were installed in the tested environment but are not required by this app.

To record the exact versions installed on a bench, run:

```bash
bench version
```

## Installation

Run the following commands from your bench directory:

```bash
bench get-app https://github.com/grayhatdevelopers/frappe_overtime_management.git --branch main
bench --site your-site.example install-app overtime_management
bench --site your-site.example migrate
```

The installation includes:

- an **Is Overtime** field on Timesheet Detail;
- an **Overtime** earning Salary Component; and
- an **Overtime Manager** role.

## Configuration

Open **Overtime Settings** and configure:

| Setting | Description | Default |
| --- | --- | ---: |
| OT Basis Salary Component | Salary component used as the calculation base | Required |
| Standard Working Hours Per Month | Hours used to calculate the base hourly rate | 160 |
| OT Multiplier | Multiplier applied to the base hourly rate | 1.0 |
| Unreported OT Lookback (Days) | Days before the period to search for unclaimed overtime | 30 |

Each employee must have a submitted Salary Structure Assignment. The selected basis component must have a fixed amount or use the formula `base`.

## Usage

1. Mark eligible rows as **Is Overtime** in a Timesheet and submit it.
2. Create an **Overtime Entry** for the company and period.
3. Click **Get Employees** and submit the entry.
4. The app creates a draft **Employee Overtime** record for each employee.
5. Review the overtime details and adjust **Approved Hours** if required.
6. Submit Employee Overtime to create the Additional Salary record.

The overtime amount is calculated as:

```text
Hourly Rate = Base Salary / Standard Working Hours Per Month * OT Multiplier
OT Amount   = Hourly Rate * Approved Overtime Hours
```

Cancelling Employee Overtime also cancels its linked Additional Salary.

## Development

Run tests with:

```bash
bench --site your-site.example run-tests --app overtime_management
```

Run formatting and lint checks with:

```bash
cd apps/overtime_management
pre-commit install
pre-commit run --all-files
```

## License

MIT. See [license.txt](license.txt).
