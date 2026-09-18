# Frappe Overtime Management

Turn approved overtime from Timesheets into payroll-ready Additional Salary records.

A focused overtime workflow for Frappe HR teams that use recorded work—not attendance—as their source of truth.

Built and maintained by [Grayhat](https://grayhat.studio).

## From Timesheet to payroll

Frappe Overtime Management keeps the source work, HR review, and payroll result connected:

```text
Submitted Timesheet
  -> Timesheet Detail marked "Is Overtime"
  -> Overtime Entry for a pay period
  -> one draft Employee Overtime record per employee
  -> HR reviews and approves hours
  -> submitted Additional Salary using the "Overtime" component
```

Only rows from submitted Timesheets are eligible. A Timesheet Detail row already linked to a non-cancelled Employee Overtime record is excluded, preventing the same work from being claimed twice.

The app can also look before the selected pay period for missed overtime. These rows remain traceable and are marked **Prior Period** during review.

## What you can do

- Process overtime in bulk through **Overtime Entry**.
- Review overtime per employee through **Employee Overtime**.
- Use monthly, fortnightly, weekly, or custom pay periods.
- Configure a lookback window for previously missed overtime.
- Keep logged hours separate from approved hours.
- Trace every claim to its project, task, activity, Timesheet, and source row.
- Calculate pay from an employee's assigned Salary Structure.
- Configure standard monthly hours and an overtime multiplier.
- Create Additional Salary automatically when overtime is submitted.
- Cancel the linked Additional Salary when Employee Overtime is cancelled.
- Prevent overlapping periods and duplicate claims.
- Give reviewers access through the dedicated **Overtime Manager** role.

## Requirements

Version `0.2.0` supports the version 16 release line and has been tested with:

| App | Tested version |
| --- | --- |
| Frappe Framework | Version 16 |
| ERPNext | `v16.28.0` |
| Frappe HR | `v16.7.1` |

Frappe HR and ERPNext are required.

## Installation

From your bench directory, run:

```bash
bench get-app https://github.com/grayhatdevelopers/frappe_overtime_management.git --branch main
bench --site your-site.example install-app overtime_management
bench --site your-site.example migrate
```

Installation adds:

- an **Is Overtime** field to Timesheet Detail;
- an **Overtime** earning Salary Component; and
- an **Overtime Manager** role.

## Configure overtime

Open **Overtime Settings** and set:

| Setting | Description | Default |
| --- | --- | ---: |
| OT Basis Salary Component | Salary component used as the calculation base | Required |
| Standard Working Hours Per Month | Hours used to calculate the base hourly rate | 160 |
| OT Multiplier | Multiplier applied to the base hourly rate | 1.0 |
| Unreported OT Lookback (Days) | Days before the period to search for unclaimed overtime | 30 |

Each employee needs a submitted Salary Structure Assignment. The selected basis component must have a fixed amount or use the formula `base`.

## Process overtime

1. Mark eligible rows as **Is Overtime** in a Timesheet and submit it.
2. Create an **Overtime Entry** for the company and pay period.
3. Select **Get Employees**, then submit the entry.
4. Open the draft **Employee Overtime** record created for each employee.
5. Review the source rows and adjust **Approved Hours** where required.
6. Submit Employee Overtime to create the Additional Salary record.

The payable amount is calculated as:

```text
Hourly Rate = Base Salary / Standard Working Hours Per Month * OT Multiplier
OT Amount   = Hourly Rate * Approved Overtime Hours
```

Cancelling Employee Overtime also cancels its linked Additional Salary.

## Development

Run the app's tests from a bench that has Frappe, ERPNext, and Frappe HR installed:

```bash
bench --site your-site.example run-tests --app overtime_management
```

Run formatting and lint checks from the app directory:

```bash
cd apps/overtime_management
pre-commit install
pre-commit run --all-files
```

### Creating a release

Releases are published automatically when a semantic-version tag is pushed. The tag must match the
version in `overtime_management/__init__.py`.

```bash
# First update __version__, commit it, and then create the matching tag.
git tag -a v0.3.0 -m "Release v0.3.0"
git push origin v0.3.0
```

The release workflow validates the tag, runs the pre-commit checks, builds the Python wheel and source
distribution, verifies both artifacts, and attaches them to a GitHub Release with generated notes.

## Help and project links

- [Issue tracker](https://github.com/grayhatdevelopers/frappe_overtime_management/issues)
- [Frappe Framework](https://github.com/frappe/frappe)
- [Frappe HR](https://github.com/frappe/hrms)
- [Grayhat](https://grayhat.studio)

For support and other enquiries, email [info@grayhat.studio](mailto:info@grayhat.studio).

## Contributing

Contributions are welcome. Open an issue to report a bug or discuss a change before submitting a pull request.

## License

Frappe Overtime Management is built by [Grayhat](https://grayhat.studio) and released under the [MIT License](license.txt).
