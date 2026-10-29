import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";
import openapiTS, { astToString } from "openapi-typescript";

const source = new URL("../contracts/gate0.openapi.json", import.meta.url);
const target = new URL("../src/lib/gate0.generated.ts", import.meta.url);
const document = JSON.parse(await fs.readFile(source, "utf8"));
// Required-only anyOf branches become `unknown` in this generator version.
// Express the same presence constraint as typed intersections for generation only.
// The frozen JSON schema used by validators is never changed.
const input = document.components.schemas.WorkingLineInput;
const { anyOf, ...base } = input;
document.components.schemas.WorkingLineInput = {
  allOf: [
    base,
    {
      anyOf: anyOf.map((branch) => ({
        type: "object",
        required: branch.required,
        properties: Object.fromEntries(
          branch.required.map((key) => [key, base.properties[key]]),
        ),
      })),
    },
  ],
};
const output =
  "// Generated from the frozen Gate 0 contract. Run npm run types:generate.\n" +
  astToString(await openapiTS(document, { defaultNonNullable: false }));
if (process.argv.includes("--check")) {
  // Git may check generated text out with CRLF on Windows; compare its content.
  if ((await fs.readFile(target, "utf8")).replaceAll("\r\n", "\n") !== output) {
    throw new Error(
      `Contract types drifted: regenerate ${fileURLToPath(target)}.`,
    );
  }
  console.log("Generated contract types match the frozen schema.");
} else {
  await fs.writeFile(target, output);
  console.log("Generated Gate 0 TypeScript types.");
}
