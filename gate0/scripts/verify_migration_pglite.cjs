const fs = require("fs");
const path = require("path");

async function main() {
  const root = path.resolve(__dirname, "..");
  const moduleRoot = process.env.GATE0_PGLITE_MODULE;
  const moduleName = moduleRoot ? path.join(moduleRoot, "dist", "index.cjs") : "@electric-sql/pglite";
  const { PGlite } = require(moduleName);
  const sql = fs.readFileSync(path.join(root, "migrations", "0001_baseline.sql"), "utf8");
  const db = new PGlite();
  try {
    await db.exec(sql);
    const tables = await db.query(
      "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name"
    );
    const triggerEvents = await db.query(
      "SELECT trigger_name,event_manipulation FROM information_schema.triggers WHERE trigger_schema='public' ORDER BY trigger_name,event_manipulation"
    );
    const approvalEvents = triggerEvents.rows
      .filter((row) => row.trigger_name === "approval_request_snapshot_guard")
      .map((row) => row.event_manipulation)
      .sort();
    if (tables.rows.length !== 18) throw new Error(`expected 18 tables, got ${tables.rows.length}`);
    if (approvalEvents.join(",") !== "DELETE,UPDATE") {
      throw new Error(`approval guard events are ${approvalEvents.join(",") || "missing"}`);
    }
    process.stdout.write(JSON.stringify({
      pglite_version: "0.5.10",
      tables: tables.rows.map((row) => row.table_name),
      table_count: tables.rows.length,
      trigger_event_count: triggerEvents.rows.length,
      approval_guard_events: approvalEvents,
    }));
  } finally {
    await db.close();
  }
}

main().catch((error) => {
  console.error(error.stack || String(error));
  process.exit(1);
});
