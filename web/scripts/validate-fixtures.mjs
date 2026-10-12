import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import Ajv2020 from "ajv/dist/2020.js";

const contractDir = new URL("../../contract/", import.meta.url).pathname;
const bundle = JSON.parse(readFileSync(join(contractDir, "schema/contract.schema.json"), "utf8"));
const ajv = new Ajv2020({ strict: false, allErrors: true });
ajv.addSchema(bundle, "contract");

const roots = {
  "report_contrast.json": "Report",
  "report_normative.json": "Report",
  "dataset_manifest.json": "DatasetManifest",
  "job_events.json": "JobEvent",
  "library.json": "LibraryListing",
};

let failures = 0;
for (const file of readdirSync(join(contractDir, "fixtures")).sort()) {
  const root = roots[file];
  if (!root) throw new Error(`fixture ${file} has no root type registered`);
  const payload = JSON.parse(readFileSync(join(contractDir, "fixtures", file), "utf8"));
  const items = Array.isArray(payload) ? payload : [payload];
  const validate = ajv.compile({ $ref: `contract#/properties/${root}` });
  for (const item of items) {
    if (!validate(item)) {
      failures += 1;
      console.error(`${file} violates ${root}:`, JSON.stringify(validate.errors, null, 2));
    }
  }
  console.log(`${file}: ${items.length} payload(s) valid as ${root}`);
}
process.exit(failures === 0 ? 0 : 1);
