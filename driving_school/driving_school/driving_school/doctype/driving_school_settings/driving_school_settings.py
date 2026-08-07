from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document


class DrivingSchoolSettings(Document):
	def validate(self):
		if (
			self.business_start_time
			and self.business_end_time
			and self.business_end_time <= self.business_start_time
		):
			frappe.throw(_("Business end time must be after business start time."))

		if self.lesson_duration_minutes and self.lesson_duration_minutes <= 0:
			frappe.throw(_("Lesson duration must be greater than zero."))

		if self.max_lessons_per_week and self.max_lessons_per_week <= 0:
			frappe.throw(_("Max lessons per week must be greater than zero."))
