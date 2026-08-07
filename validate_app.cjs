#!/usr/bin/env node
/**
 * Structural validator for the driving_school Frappe app.
 * Run:  node validate_app.js
 * Checks: JSON validity, DocType JSON integrity, module folders, links,
 * fetch_from targets, permissions, reports, hooks references, portal pages.
 */
const fs = require("fs");
const path = require("path");

const APP = "driving_school";
const errors = [];
const warnings = [];

// Core Frappe doctypes that may be referenced by Link fields
const CORE_DOCTYPES = new Set([
	"User",
	"Company",
	"Asset",
	"Sales Invoice",
	"Role",
	"Has Role",
	"File",
	"ToDo",
	"Comment",
]);

function walk(dir, out = []) {
	if (!fs.existsSync(dir)) return out;
	for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
		const full = path.join(dir, entry.name);
		if (entry.isDirectory()) walk(full, out);
		else out.push(full);
	}
	return out;
}

function readJson(file) {
	try {
		return JSON.parse(fs.readFileSync(file, "utf8"));
	} catch (e) {
		errors.push(`Invalid JSON in ${file}: ${e.message}`);
		return null;
	}
}

const allFiles = walk(APP).map((f) => f.split(path.sep).join("/"));
const jsonFiles = allFiles.filter((f) => f.endsWith(".json"));
const pyFiles = allFiles.filter((f) => f.endsWith(".py"));

// ---------------------------------------------------------------- doctypes
const doctypeFiles = jsonFiles.filter((f) => f.includes("/doctype/"));
const doctypes = {}; // name -> {data, file}

for (const file of doctypeFiles) {
	const data = readJson(file);
	if (!data) continue;
	if (data.doctype !== "DocType") {
		errors.push(`${file}: expected "doctype": "DocType"`);
		continue;
	}
	if (!data.name) {
		errors.push(`${file}: missing "name"`);
		continue;
	}
	if (doctypes[data.name]) {
		errors.push(`Duplicate DocType name "${data.name}" (${file} and ${doctypes[data.name].file})`);
	}
	doctypes[data.name] = { data, file };
}

const moduleFromName = (name) => name.toLowerCase().replace(/\s+/g, "_");

for (const [name, { data, file }] of Object.entries(doctypes)) {
	// module folder must exist
	const moduleFolder = `${APP}/${APP}/${moduleFromName(data.module)}`;
	if (!fs.existsSync(moduleFolder)) {
		errors.push(`${file}: module folder "${moduleFolder}" does not exist for module "${data.module}"`);
	}

	// controller + __init__ for non-child, non-single
	if (!data.istable && !data.issingle) {
		const folder = path.dirname(file).split(path.sep).join("/");
		const controller = `${folder}/${path.basename(file).replace(".json", ".py")}`;
		if (!fs.existsSync(controller)) {
			errors.push(`${file}: missing controller file ${controller}`);
		}
	}

	// child doctypes referenced via Table must exist
	const fieldnames = new Set();
	for (const field of data.fields || []) {
		if (!field.fieldname) {
			errors.push(`${file}: field without fieldname`);
			continue;
		}
		if (fieldnames.has(field.fieldname)) {
			errors.push(`${file}: duplicate fieldname "${field.fieldname}"`);
		}
		fieldnames.add(field.fieldname);

		if (field.fieldtype === "Link") {
			if (!doctypes[field.options] && !CORE_DOCTYPES.has(field.options)) {
				errors.push(`${file}: Link field "${field.fieldname}" points to unknown doctype "${field.options}"`);
			}
		}
		if (field.fieldtype === "Table") {
			if (!doctypes[field.options]) {
				errors.push(`${file}: Table field "${field.fieldname}" points to unknown child doctype "${field.options}"`);
			} else if (!doctypes[field.options].data.istable) {
				errors.push(`${file}: Table field "${field.fieldname}" -> "${field.options}" is not istable`);
			}
		}
		// fetch_from must be link.target_field
		if (field.fetch_from && typeof field.fetch_from === "string" && field.fetch_from.includes(".")) {
			const [linkField, targetField] = field.fetch_from.split(".");
			const linkDef = (data.fields || []).find((f) => f.fieldname === linkField);
			if (!linkDef) {
				errors.push(`${file}: fetch_from "${field.fetch_from}" references missing link field "${linkField}"`);
			} else if (linkDef.fieldtype !== "Link") {
				errors.push(`${file}: fetch_from "${field.fetch_from}" - "${linkField}" is not a Link field`);
			} else {
				const target = doctypes[linkDef.options];
				if (target) {
					const targetFields = new Set((target.data.fields || []).map((f) => f.fieldname));
					if (!targetFields.has(targetField)) {
						errors.push(
							`${file}: fetch_from "${field.fetch_from}" - "${linkDef.options}" has no field "${targetField}"`
						);
					}
				}
			}
		}
	}

	// field_order must cover all fields (allowing for section/column breaks)
	if (Array.isArray(data.field_order)) {
		const orderSet = new Set(data.field_order);
		for (const f of data.fields || []) {
			if (!orderSet.has(f.fieldname)) {
				errors.push(`${file}: field "${f.fieldname}" missing from field_order`);
			}
		}
	}

	// naming rule sanity
	if (data.autoname && data.naming_rule !== "Expression") {
		errors.push(`${file}: autoname present but naming_rule is "${data.naming_rule}"`);
	}
	if (data.istable && data.permissions && data.permissions.length) {
		errors.push(`${file}: istable doctype should not have permissions`);
	}
	if (!data.istable && !data.issingle && !data.autoname && !data.allow_rename) {
		errors.push(`${file}: doctype has no autoname and no allow_rename`);
	}

	// module must be declared in modules.txt
	const modules = fs.readFileSync(`${APP}/modules.txt`, "utf8").split("\n").map((s) => s.trim()).filter(Boolean);
	if (!modules.includes(data.module)) {
		errors.push(`${file}: module "${data.module}" not declared in modules.txt`);
	}
}

// ---------------------------------------------------------------- reports
const reportFiles = jsonFiles.filter((f) => f.includes("/report/"));
for (const file of reportFiles) {
	const data = readJson(file);
	if (!data || data.doctype !== "Report") continue;
	if (data.is_standard !== "Yes") {
		errors.push(`${file}: is_standard must be "Yes"`);
	}
	if (data.report_type !== "Script Report") {
		errors.push(`${file}: report_type must be "Script Report"`);
	}
	if (!doctypes[data.ref_doctype]) {
		errors.push(`${file}: ref_doctype "${data.ref_doctype}" is not a doctype in this app`);
	}
	const folder = path.dirname(file).split(path.sep).join("/");
	if (!fs.existsSync(`${folder}/${path.basename(file, ".json")}.py`)) {
		errors.push(`${file}: missing report python script`);
	}
	if (!fs.existsSync(`${folder}/${path.basename(file, ".json")}.js`)) {
		errors.push(`${file}: missing report js file`);
	}
}

// ---------------------------------------------------------------- hooks
const hooks = fs.readFileSync(`${APP}/hooks.py`, "utf8");
// module path = everything before the last dotted segment (the function name)
// the dotted path already starts with the app name
const modulePath = (dotted) => dotted.split(".").slice(0, -1).join("/") + ".py";

const mAfter = hooks.match(/after_install\s*=\s*"([^"]+)"/);
if (mAfter) {
	const modFile = modulePath(mAfter[1]);
	if (!fs.existsSync(modFile)) {
		errors.push(`hooks.py: after_install module file ${modFile} not found`);
	}
} else {
	errors.push("hooks.py: after_install not defined");
}

// scheduler events
for (const m of hooks.matchAll(/"(daily|hourly)":\s*\[\s*"([^"]+)"/g)) {
	const modPath = modulePath(m[2]);
	if (!fs.existsSync(modPath)) {
		errors.push(`hooks.py: scheduler "${m[1]}" -> ${m[2]} module file not found`);
	}
}

// asset references
for (const m of hooks.matchAll(/"(?:app_include_css|app_include_js)"\s*=\s*\[([^\]]*)\]/gs)) {
	for (const am of m[1].matchAll(/"(\/assets\/[^"]+)"/g)) {
		const rel = am[1].replace(/^\/assets\//, "").replace(/^driving_school\//, `${APP}/public/`);
		if (!fs.existsSync(rel)) {
			errors.push(`hooks.py: asset "${am[1]}" not found (looked at ${rel})`);
		}
	}
}

// ---------------------------------------------------------------- portal pages
const wwwDirs = fs
	.readdirSync(`${APP}/www`, { withFileTypes: true })
	.filter((e) => e.isDirectory())
	.map((e) => e.name);
for (const dir of wwwDirs) {
	for (const ext of ["py", "html", "js"]) {
		if (!fs.existsSync(`${APP}/www/${dir}/index.${ext}`)) {
			errors.push(`www/${dir}: missing index.${ext}`);
		}
	}
}

// ---------------------------------------------------------------- api method cross-check
const apiSrc = fs.readFileSync(`${APP}/api.py`, "utf8");
const apiMethods = new Set([...apiSrc.matchAll(/^def\s+(\w+)/gm)].map((m) => m[1]));
for (const jsFile of allFiles.filter((f) => f.endsWith(".js"))) {
	const src = fs.readFileSync(jsFile, "utf8");
	for (const m of src.matchAll(/driving_school\.api\.(\w+)/g)) {
		if (!apiMethods.has(m[1])) {
			errors.push(`${jsFile}: calls unknown api method "driving_school.api.${m[1]}"`);
		}
	}
}

// ---------------------------------------------------------------- py file basic checks
for (const py of pyFiles) {
	const src = fs.readFileSync(py, "utf8");
	if (src.includes("\t\t\t\t\t")) warnings.push(`${py}: deep indentation (possible tab/space mix)`);
	// simple brace/paren balance check for common mistakes
	const open = (src.match(/\(/g) || []).length;
	const close = (src.match(/\)/g) || []).length;
	if (open !== close) errors.push(`${py}: unbalanced parentheses (${open} open / ${close} close)`);
}

// ---------------------------------------------------------------- summary
console.log("=".repeat(60));
console.log(`Validated ${doctypeFiles.length} doctype JSONs, ${reportFiles.length} report JSONs, ${pyFiles.length} python files`);
console.log("=".repeat(60));

if (errors.length) {
	console.log(`\n${errors.length} ERROR(S):`);
	errors.forEach((e) => console.log("  [ERR] " + e));
	process.exit(1);
}
console.log("\nNo structural errors found.");

if (warnings.length) {
	console.log(`\n${warnings.length} WARNING(S):`);
	warnings.forEach((w) => console.log("  [WARN] " + w));
} else {
	console.log("No warnings.");
}
console.log("\nDoctypes in app: " + Object.keys(doctypes).join(", "));
