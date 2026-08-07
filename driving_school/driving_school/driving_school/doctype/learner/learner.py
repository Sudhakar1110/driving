from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today


class Learner(Document):
	def validate(self):
		self.validate_email()
		self.validate_mobile_number()
		self.validate_medical_certificate()

	def validate_email(self):
		if not self.email:
			return
		existing = frappe.db.get_value(
			"Learner", {"email": self.email, "name": ["!=", self.name]}, "name"
		)
		if existing:
			frappe.throw(
				_("A learner with email {0} already exists ({1}).").format(self.email, existing)
			)

	def validate_mobile_number(self):
		if not self.mobile_number:
			return
		existing = frappe.db.get_value(
			"Learner", {"mobile_number": self.mobile_number, "name": ["!=", self.name]}, "name"
		)
		if existing:
			frappe.throw(
				_("A learner with mobile number {0} already exists ({1}).").format(
					self.mobile_number, existing
				)
			)

	def validate_medical_certificate(self):
		if self.medical_certificate_expiry and getdate(
			self.medical_certificate_expiry
		) < getdate(today()):
			frappe.msgprint(
				_("Medical certificate for {0} has expired.").format(self.learner_name),
				indicator="orange",
			)

	def on_update(self):
		self.sync_portal_user()

	def sync_portal_user(self):
		"""Create (or upgrade) the portal User for this learner."""
		if not self.email or self.status in ("Enquired", "Dropped"):
			return

		user = None
		if frappe.db.exists("User", self.email):
			user = frappe.get_doc("User", self.email)
			self.add_learner_role(user)
		else:
			user = frappe.new_doc("User")
			user.email = self.email
			user.first_name = self.learner_name
			user.send_welcome_email = False
			user.append("roles", {"role": "Learner"})
			try:
				user.insert(ignore_permissions=True)
			except Exception:
				frappe.log_error(frappe.get_traceback(), "Driving School: portal user creation failed")
				return

		if self.user != self.email:
			self.db_set("user", self.email)

	def add_learner_role(self, user):
		if not any(r.role == "Learner" for r in user.roles):
			user.append("roles", {"role": "Learner"})
			user.save(ignore_permissions=True)
