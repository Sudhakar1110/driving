from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document


class DrivingVehicle(Document):
	def validate(self):
		self.validate_vehicle_number()
		self.compute_service_due()

	def validate_vehicle_number(self):
		if not self.vehicle_number:
			frappe.throw(_("Vehicle number is required."))
		existing = frappe.db.sql(
			"""
			select name from `tabDriving Vehicle`
			where lower(vehicle_number) = lower(%(number)s) and name != %(name)s
			""",
			{"number": self.vehicle_number, "name": self.name or ""},
		)
		if existing:
			frappe.throw(
				_("Vehicle number {0} already exists ({1}).").format(self.vehicle_number, existing[0][0])
			)

	def compute_service_due(self):
		if self.last_service_odometer and self.service_interval_km:
			self.next_service_due_km = self.last_service_odometer + self.service_interval_km
