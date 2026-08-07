# Driving School Manager (driving_school)

A complete **Driving School Manager** app for **Frappe 15 / ERPNext 15** — learner
registration, lesson booking, instructor allocation, vehicle management, package
billing and a full learner self-service portal.

Built as a standalone Frappe app: it installs on bare Frappe **and** alongside
ERPNext 15. ERPNext integration points (Sales Invoice references, Asset links)
are optional and never block installation.

## Features

### Desk (staff)
- **Learner management** — registration, documents (ID, medical certificate),
  status workflow, training stages, duplicate detection, auto-created portal user
- **Lesson booking & scheduling** — conflict-free slots, calendar view,
  statuses (Requested → Confirmed → Completed / Cancelled / No Show / Waitlist),
  reschedule, cancellation fees, instructor & vehicle assignment
- **Instructor management** — licenses, categories, leave with overlap checks,
  commissions
- **Vehicle management** — register, insurance/permit/fitness expiry alerts,
  service odometer tracking
- **Packages & payments** — package deals (10 lessons + test fee), discounts,
  paid/balance tracking, payment modes, outstanding receivables
- **Theory classes & mock tests** — attendance, question bank, auto-scoring
- **Enquiry pipeline** — lead stages + one-click **Convert to Learner**
- **4 script reports** — Revenue, Outstanding Receivables, Instructor
  Performance, Vehicle Utilization (with charts & summaries)
- **Scheduled reminders** — lesson reminders (24h + 2h), document/vehicle/package
  expiry alerts (enabled in Driving School Settings)

### Portal (learner self-service) — served under the same site
| Route | What the learner can do |
|---|---|
| `/portal-home` | Dashboard: stats, package, upcoming lessons, quick actions |
| `/book-lesson` | Pick date/instructor/vehicle + free slot and book |
| `/my-lessons` | View lessons, cancel, reschedule |
| `/my-payments` | Payment history, outstanding balance, request a payment |
| `/my-progress` | Packages, mock test scores, driving tests, theory attendance |
| `/mock-test` | Take a scored 10-question mock theory test |

## DocTypes

`Learner` · `Learner Document` (child) · `Driving Instructor` ·
`Instructor Vehicle Category` (child) · `Instructor Leave` · `Driving Vehicle` ·
`Learner Package` · `Lesson Booking` · `Theory Class` ·
`Theory Class Attendance` · `Mock Test Question` · `Mock Test Answer` (child) ·
`Mock Test Attempt` · `Driving Test` · `Learner Payment` · `Learner Feedback` ·
`Enquiry` · `Driving School Branch` · `Driving School Settings` (single)

## Installation (bench, Frappe v15)

```bash
# inside your bench directory (init with: bench init --frappe-branch version-15)
cd frappe-bench

# either copy this folder into apps/driving_school ...
cp -r <path-to>/driving_school apps/driving_school

# ... or fetch from a git repo
# bench get-app https://github.com/<your-org>/driving_school

bench --site <your-site> install-app driving_school
bench migrate
bench build
bench restart
```

> ERPNext optional: `bench --site <site> install-app erpnext` first if you want
> Sales Invoice / Asset integration. The app runs fine without it.

### Roles created on install
`Driving School Admin`, `Driving School Manager`, `Driving Instructor`,
`Driving School Accounts` (desk access) and `Learner` (portal only).

### Demo data (optional)
```bash
bench --site <your-site> execute driving_school.demo.create_demo_data
```

### First steps
1. Go to **Driving School Settings** and review defaults (business hours,
   lesson duration, cancellation policy, reminders).
2. Create a **Branch**, **Instructor(s)**, **Vehicle(s)**.
3. Register a **Learner** (a portal user is created automatically from the email —
   use Forgot Password on `/login` to set a password).
4. Create a **Learner Package** for the learner and record the payment.
5. Book lessons from the desk or have the learner use `/book-lesson`.

## Validation

```bash
node validate_app.cjs  # structural checks (JSON, links, modules, hooks, pages)
```

## Notes
- Portal payments create a **request**; the school marks it `Received` from the
  desk (cash/UPI/bank). A payment-gateway checkout can be added on top.
- Currency display follows the site default.
- This app is a demo-grade implementation, not an official Frappe/ERPNext product.
