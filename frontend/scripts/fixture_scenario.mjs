// Developer-only controls for the loopback fixture harness.
const [scenario = "price", ...options] = process.argv.slice(2);
const get = (name) =>
  options
    .find((value) => value.startsWith(`--${name}=`))
    ?.split("=")
    .slice(1)
    .join("=");
const base = `http://127.0.0.1:${Number(process.env.KIRA_FIXTURE_PORT ?? 4191)}/api/v1`;
try {
  const response = await fetch(`${base}/__fixture/reset`, {
    method: "POST",
    headers: {
      Authorization: "Bearer fixture-owner",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      scenario,
      saveResult: get("save") ?? "ready",
      error: get("error") ?? null,
      wakeDelayMs: Number(get("wake-delay") ?? 0),
    }),
  });
  if (!response.ok)
    throw new Error("Choose price, ready, stock, candidate or pending.");
  console.log(JSON.stringify(await response.json()));
  console.log(
    "Fixed synthetic snapshots selected. Refresh the saved order or reconnect the fixture session to load them.",
  );
} catch (error) {
  console.error(
    error.message === "fetch failed"
      ? "Start npm run mock:api first."
      : error.message,
  );
  process.exitCode = 1;
}
