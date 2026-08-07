from __future__ import unicode_literals

import os
import sys
import traceback

import frappe


def run():
	"""Diagnose why driving_school DocTypes / Workspace may be missing on the site.

	Run:  bench --site <your-site> execute driving_school.install_diag.run
	"""
	print("=" * 62)
	print("driving_school install diagnostic")
	print("frappe version:", getattr(frappe, "__version__", "unknown"))
	print("=" * 62)

	print("\n[1] Apps installed on this site:")
	try:
		for app in frappe.get_installed_apps():
			print("   -", app)
	except Exception as e:
		print("   ERROR:", type(e).__name__, e)

	print("\n[2] WHERE Python loads 'driving_school' from (the critical check):")
	try:
		mod = frappe.get_module("driving_school")
		print("   driving_school.__file__:", getattr(mod, "__file__", "?"))
		print("   get_app_path            :", frappe.get_app_path("driving_school"))
	except Exception as e:
		print("   ERROR importing driving_school:", type(e).__name__, e)

	print("\n[3] sys.path entries containing a driving_school folder (catches stale copies):")
	try:
		found = False
		for p in sys.path:
			cand = os.path.join(p, "driving_school")
			if p and os.path.isdir(cand):
				found = True
				print("   candidate:", cand)
		if not found:
			print("   none (package loads from an editable install elsewhere)")
	except Exception as e:
		print("   ERROR:", type(e).__name__, e)

	print("\n[4] module map (frappe.local.app_modules):")
	try:
		apps = frappe.local.app_modules or {}
		print("   app_modules['driving_school']:", apps.get("driving_school"))
		print("   module_app['driving_school'] :", frappe.local.module_app.get("driving_school"))
	except Exception as e:
		print("   ERROR:", type(e).__name__, e)

	print("\n[5] modules.txt on disk (read directly, bypasses cache):")
	try:
		mp = frappe.get_app_path("driving_school", "modules.txt")
		print("   path:", mp)
		print("   exists:", os.path.exists(mp))
		print("   module list:", frappe.get_module_list("driving_school"))
	except Exception as e:
		print("   ERROR:", type(e).__name__, e)

	print("\n[6] sync path probe (exactly what frappe.model.sync.sync_for walks):")
	try:
		mod = frappe.get_module("driving_school.driving_school")
		folder = os.path.dirname(getattr(mod, "__file__", "") or "")
		print("   driving_school.driving_school.__file__:", getattr(mod, "__file__", "?"))
		print("   folder:", folder)
		print("   folder exists:", os.path.exists(folder))
		if os.path.exists(folder):
			print("   folder contents:", sorted(os.listdir(folder)))
		doctype_dir = os.path.join(folder, "doctype")
		print("   doctype dir exists:", os.path.exists(doctype_dir))
		if os.path.exists(doctype_dir):
			print("   doctype subfolders:", len(os.listdir(doctype_dir)))
			for n in sorted(os.listdir(doctype_dir)):
				print("      -", n)
		else:
			print("   >>> NO doctype folder at", doctype_dir, "- this is why sync finds nothing")
	except Exception as e:
		print("   ERROR resolving module:", type(e).__name__, e)

	print("\n[7] DocTypes in database with module 'Driving School':")
	try:
		names = frappe.get_all(
			"DocType", filters={"module": "Driving School"}, pluck="name", limit_page_length=100
		)
		print("   count:", len(names))
		for n in names:
			print("      -", n)
	except Exception as e:
		print("   ERROR querying DocType:", type(e).__name__, e)

	print("\n[8] Workspaces in database with module 'Driving School':")
	try:
		names = frappe.get_all(
			"Workspace", filters={"module": "Driving School"}, pluck="name", limit_page_length=100
		)
		print("   count:", len(names))
		for n in names:
			print("      -", n)
	except Exception as e:
		print("   ERROR querying Workspace:", type(e).__name__, e)

	print("\n[9] Sample tables exist?")
	try:
		print("   tabLearner:", frappe.db.table_exists("tabLearner"))
		print("   tabLesson Booking:", frappe.db.table_exists("tabLesson Booking"))
	except Exception as e:
		print("   ERROR:", type(e).__name__, e)

	print("\n" + "=" * 62)
	print("Paste this output in the chat so the root cause can be fixed.")
	print("=" * 62)


def resync():
	"""Force re-sync of all driving_school DocTypes, Reports and Workspace.

	This is the same schema sync that `bench migrate` performs, but it first
	wipes the stale module-map cache in Redis and rebuilds it from disk, so it
	works even when a broken cache made migrate silently skip the app.

	Run:  bench --site <your-site> execute driving_school.install_diag.resync
	"""
	try:
		# 1. wipe the cached module map so it gets rebuilt from disk
		frappe.clear_cache()
		frappe.cache.delete_value(["app_modules", "installed_app_modules", "all_apps"])

		# 2. rebuild the module map from the apps on this bench
		frappe.setup_module_map(include_all_apps=True)
		apps = frappe.local.app_modules or {}
		print("module map after rebuild:", apps.get("driving_school"))
		print("modules.txt on disk     :", frappe.get_module_list("driving_school"))

		mod = frappe.get_module("driving_school.driving_school")
		print("module file             :", getattr(mod, "__file__", "?"))

		if not apps.get("driving_school"):
			print(
				"\nERROR: driving_school module was NOT registered. The server is likely "
				"running OLD code (modules.txt at the wrong path).\n"
				"Fix: cd ~/frappe-bench-v15/apps/driving_school && "
				"git fetch upstream main && git reset --hard upstream/main\n"
				"then run this resync again."
			)
			return

		# 3. run the exact v15 schema sync for this app (doctypes + reports + workspace)
		print("\nSyncing driving_school...")
		from frappe.model.sync import sync_for

		sync_for("driving_school", force=True)
		frappe.db.commit()

		# 4. report the result
		names = frappe.get_all(
			"DocType", filters={"module": "Driving School"}, pluck="name", limit_page_length=100
		)
		print("\nDocTypes in DB with module 'Driving School':", len(names))
		for n in names:
			print("   -", n)

		ws = frappe.get_all(
			"Workspace", filters={"module": "Driving School"}, pluck="name", limit_page_length=100
		)
		print("\nWorkspaces in DB:", ws)

		frappe.clear_cache()
		print("\nDone. Restart bench (bench restart), log in as Administrator and")
		print("hard-refresh the desk (Ctrl+Shift+R) - 'Driving School' will appear.")
	except Exception:
		traceback.print_exc()
		print("\nIf you see a traceback above, paste it in the chat - it tells us")
		print("exactly what still needs fixing.")
