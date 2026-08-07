from __future__ import unicode_literals

__version__ = "15.0.0"

app_name = "driving_school"
app_title = "Driving School"
app_publisher = "Driving School"
app_description = "Driving School Manager - learner registration, lesson booking, instructor allocation, vehicle management and payment tracking for Frappe / ERPNext 15"
app_email = "support@example.com"
app_license = "mit"

# Install / uninstall
after_install = "driving_school.install.after_install"
before_uninstall = "driving_school.install.before_uninstall"

# Assets
app_include_css = ["/assets/driving_school/css/driving_school.css"]
app_include_js = ["/assets/driving_school/js/calendar.js"]

# Scheduled jobs
scheduler_events = {
	"daily": [
		"driving_school.scheduler.daily"
	],
	"hourly": [
		"driving_school.scheduler.hourly"
	],
}

# Website / portal
website_route_rules = []
