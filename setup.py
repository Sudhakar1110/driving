from setuptools import find_packages, setup

name = "driving_school"
version = "15.0.0"

setup(
	name="driving_school",
	version="15.0.0",
	description="Driving School Manager - learner registration, lesson booking, instructor allocation and payment tracking for Frappe/ERPNext 15",
	author="Sujai",
	author_email="sujaiit0696@gmail.com",
	packages=find_packages(),
	include_package_data=True,
	zip_safe=False,
)
