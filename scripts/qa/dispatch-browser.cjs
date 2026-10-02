// Browser smoke test for Dispatch ingestion + configuration + dashboard.
// Serve backend on :8765 and generate /tmp/dispatch100.json first.
// Requires Playwright and Chromium via CHROMIUM_PATH. All APIs are mocked.
const {chromium} = require("playwright");
const fs = require("fs");
const assert = require("node:assert/strict");

const result = JSON.parse(
  fs.readFileSync(
    process.env.DATION_QA_RESULT || "/tmp/dispatch100.json",
    "utf8",
  ),
);

const ids = {
  orders: "00000000-0000-4000-8000-000000000001",
  fleet: "00000000-0000-4000-8000-000000000002",
};

const orders = {
  id: ids.orders,
  dataset_type: "orders",
  original_filename: "orders.csv",
  label: "Semana 40",
  row_count: 100,
  created_at: "2026-10-01T00:00:00Z",
  profile_json: {
    valid: true,
    counts: {errors: 0, warnings: 0},
    profile: {
      total_units: 2682,
      total_weight_kg: 2384000,
      routes: 28,
      origins: 3,
      destinations: 10,
      date_from: "2026-10-01",
      date_to: "2026-10-10",
      max_order_kg: 61600,
      priority_mix: {High: 27, Normal: 62, Low: 11},
      delivery_days: {min: 1, max: 5},
      daily: [
        {date: "2026-10-01", orders: 7, kg: 153900},
        {date: "2026-10-09", orders: 13, kg: 351800},
      ],
    },
  },
};

const fleet = {
  id: ids.fleet,
  dataset_type: "fleet",
  original_filename: "fleet.csv",
  label: "Flota sintética",
  row_count: 4,
  created_at: "2026-10-01T00:00:00Z",
  is_default: true,
  profile_json: {
    valid: true,
    counts: {errors: 0, warnings: 0},
    profile: {
      fleet: result.fleet,
      types: 4,
      own_units_per_day: 11,
      own_capacity_kg_per_day: 167000,
      has_third_party: true,
    },
  },
};

const contracts = {
  formats: {
    orders: {
      schema: "orders_v1",
      label: "Órdenes de envío",
      role: "Qué hay que entregar. Cambian en cada corrida.",
      columns: [
        {
          name: "order_id",
          required: true,
          rule: "Texto único",
          example: "SHP-0001",
          description: "Identifica la orden.",
        },
      ],
    },
    fleet: {
      schema: "fleet_v1",
      label: "Flota disponible",
      role: "Con qué camiones se puede despachar.",
      columns: [
        {
          name: "vehicle_type",
          required: true,
          rule: "Texto único",
          example: "Truck_L",
          description: "Tipo de camión.",
        },
      ],
    },
  },
};

result.inputs.orders = {
  ...result.inputs.orders,
  dataset_id: ids.orders,
  filename: "orders.csv",
};
result.inputs.fleet = {
  ...result.inputs.fleet,
  dataset_id: ids.fleet,
  filename: "fleet.csv",
  label: "Flota sintética",
  created_at: fleet.created_at,
};

(async () => {
  const browser = await chromium.launch({
    executablePath: process.env.CHROMIUM_PATH || "/tmp/chromium",
    args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
    headless: true,
  });

  try {
    const page = await browser.newPage({
      viewport: {width: 1440, height: 1000},
      httpCredentials: {
        username: "dation",
        password: process.env.DATION_ACCESS_PASSWORD || "dispatch-qa",
      },
    });

    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));

    let runId = "00000000-0000-4000-8000-000000000003";
    let storageAvailable = true;

    await page.route("**/api/**", async (route) => {
      const url = new URL(route.request().url());
      const path = url.pathname;
      let data = {};

      if (path === "/api/dispatch/status") {
        data = storageAvailable
          ? {
            available: true,
            engine_version: "1.0.0",
            checks: [],
            message: null,
          }
          : {
            available: false,
            engine_version: "1.0.0",
            message: "Activación pendiente: la validación local sigue disponible.",
            checks: [
              {
                id: "datasets_schema",
                label: "Esquema de datasets",
                ok: false,
                detail: "Columnas nuevas no visibles.",
                fix: "Aplicá las migraciones y recargá el esquema.",
              },
            ],
          };
      } else if (path === "/api/dispatch/contracts") {
        data = contracts;
      } else if (path === "/api/datasets") {
        const type = url.searchParams.get("type");
        data = {
          items: type === "orders"
            ? [orders]
            : type === "fleet"
              ? [fleet]
              : [],
        };
      } else if (path.endsWith("/profile")) {
        data = {dataset: path.includes(ids.orders) ? orders : fleet};
      } else if (path === "/api/runs/preflight") {
        data = {
          valid: true,
          warnings: result.inputs.preflight.warnings,
          errors: [],
          anomalies: [],
          findings: [
            {
              id: "late_orders",
              severity: "warning",
              title: "7 órdenes llegarán tarde aunque salgan el primer día",
              consequence: "Resultado operacional reservado para la siguiente etapa.",
              items: [],
            },
          ],
          readiness: {
            can_continue: true,
            blockers: [],
            reason: null,
          },
        };
      } else if (path === "/api/runs" && route.request().method() === "POST") {
        const body = route.request().postDataJSON();
        assert.equal(body.configuration.objective, "custom");
        assert.equal(
          Object.values(body.configuration.weights).reduce(
            (sum, value) => sum + value,
            0,
          ),
          1,
        );
        runId = url.searchParams.get("run_id");
        data = {
          id: runId,
          status: "completed",
          result_json: result,
        };
      } else if (path === "/api/runs") {
        data = {items: []};
      } else if (path.endsWith("/interpretation")) {
        data = {messages: [], explanation: null};
      } else if (path.startsWith("/api/runs/")) {
        data = {
          id: runId,
          status: "completed",
          result_json: result,
        };
      } else if (path === "/api/workspace/summary") {
        data = {datasets: 2, runs: 0};
      } else if (path === "/api/system/supabase-check") {
        data = {ok: true};
      } else if (path === "/api/system/llm-status") {
        data = {configured: false};
      }

      await route.fulfill({json: data});
    });

    await page.goto(
      process.env.DATION_QA_URL || "http://127.0.0.1:8765/app",
    );
    await page.waitForFunction(() => window.DationDispatch);

    // State 1: activation pending must still render the full ingestion screen.
    storageAvailable = false;
    await page.evaluate(() => window.dationNavigate("logistics-data"));
    await page.locator(".dispatch-upload-screen").waitFor();
    await page.locator(".dispatch-system-banner").waitFor();
    assert.equal(
      await page.locator("[data-kind='orders']").count(),
      1,
    );
    assert.equal(
      await page.locator("[data-kind='fleet']").count(),
      1,
    );
    await page.screenshot({
      path: "/tmp/dation-upload-pending.png",
      fullPage: true,
      animations: "disabled",
    });

    // State 2: storage available, reuse existing orders and fleet.
    storageAvailable = true;
    await page.reload();
    await page.waitForFunction(() => window.DationDispatch);
    await page.evaluate(() => window.dationNavigate("logistics-data"));
    await page.locator(".dispatch-upload-screen").waitFor();

    await page
      .getByRole("button", {name: "Usar una carga anterior →"})
      .click();
    await page
      .locator(".dispatch-previous-drawer")
      .getByRole("button", {name: "Usar", exact: true})
      .click();

    await page
      .getByRole("button", {name: "Usar una flota guardada →"})
      .click();
    await page
      .locator(".dispatch-previous-drawer")
      .getByRole("button", {name: "Usar", exact: true})
      .click();

    await page.getByText("orders.csv", {exact: true}).waitFor();
    await page.getByText("100 registros", {exact: false}).waitFor();
    await page.getByText("fleet.csv", {exact: true}).waitFor();
    await page.getByText("4 registros", {exact: false}).waitFor();

    assert.equal(
      await page
        .getByText("7 órdenes llegarán tarde aunque salgan el primer día")
        .count(),
      0,
    );
    assert.equal(
      await page.getByText("Demanda vs. capacidad propia por día").count(),
      0,
    );

    const next = page.getByRole(
      "button",
      {name: "Configurar decisión →", exact: true},
    );
    await next.waitFor();
    assert.equal(await next.isEnabled(), true);

    const desktopUpload = await page.evaluate(() => ({
      width: innerWidth,
      scroll: document.documentElement.scrollWidth,
    }));
    await page.screenshot({
      path: "/tmp/dation-upload-desktop.png",
      fullPage: true,
      animations: "disabled",
    });

    await next.click();
    await page.locator("[data-review]").waitFor();
    await page.locator("[data-preset='min_time']").click();
    await page.locator("[data-slider='cost']").fill("40");
    await page.locator("[data-review]").click();
    await page.locator("[data-execute]").click();

    await page.locator("#dispatch-hero h1").waitFor();
    await page.screenshot({
      path: "/tmp/dation-dashboard-desktop.png",
      fullPage: true,
      animations: "disabled",
    });

    const downloaded = page.waitForEvent("download");
    await page.locator("[data-json]").click();
    assert.match((await downloaded).suggestedFilename(), /\.json$/);

    await page.reload();
    await page.locator("#dispatch-hero h1").waitFor();
    await page.setViewportSize({width: 390, height: 844});
    await page.locator("[data-rerun]").click();
    await page.locator("[data-review]").waitFor();
    await page.getByText("Cambiar datos", {exact: true}).click();
    await page.locator(".dispatch-upload-screen").waitFor();

    const mobileUpload = await page.evaluate(() => ({
      width: innerWidth,
      scroll: document.documentElement.scrollWidth,
    }));
    await page.screenshot({
      path: "/tmp/dation-upload-mobile.png",
      fullPage: true,
      animations: "disabled",
    });

    assert.equal(desktopUpload.scroll, desktopUpload.width);
    assert.equal(mobileUpload.scroll, mobileUpload.width);
    assert.deepEqual(errors, []);

    console.log(
      JSON.stringify({
        desktopUpload,
        mobileUpload,
        errors,
      }),
    );
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
