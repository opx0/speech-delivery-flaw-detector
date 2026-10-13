import { expect, test } from "@playwright/test";

test("real demo analysis, playback, reference audition, rubric, charts, and mobile reflow", async ({
  page,
}, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Make every word land." }),
  ).toBeVisible();
  await expect(page.locator(".example-card")).toHaveCount(3);
  await page.screenshot({
    path: testInfo.outputPath("welcome-desktop.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Explore examples" }).click();
  await page.getByLabel("Choose a speech").selectOption("new-colossus");
  const finished = page.waitForResponse(
    (response) =>
      response.url().includes("/events") && response.status() === 200,
  );
  await page
    .getByRole("button", { name: /Rushed pacing Rushed pacing injected/ })
    .click();
  await finished;
  await expect(page.getByTestId("overall-score")).toBeVisible({
    timeout: 150_000,
  });
  await expect(
    page.getByRole("heading", { name: "The New Colossus: rushed pacing" }),
  ).toBeVisible();
  await expect(page.locator(".finding-card").first()).toBeVisible();
  await page.locator(".finding-card").first().click();
  await expect(page.locator(".measurement-grid")).toBeVisible();
  await page.getByRole("button", { name: "Play passage", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Pause audio", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Pause audio", exact: true }).click();
  await page
    .getByRole("button", { name: "Gold reference", exact: true })
    .click();
  await expect(
    page.getByText("Listening to the gold recording.", { exact: false }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Play audio", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Pause audio", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Pause audio", exact: true }).click();
  await page
    .getByRole("button", { name: "Your recording", exact: true })
    .click();
  await page.getByRole("button", { name: "Adjust rubric" }).click();
  const scoreBefore = await page.getByTestId("overall-score").textContent();
  const cadenceWeight = page.getByRole("slider", { name: "Cadence weight" });
  await cadenceWeight.press("Home");
  for (let step = 0; step < 80; step++) await cadenceWeight.press("ArrowRight");
  await expect(
    page.getByRole("slider", { name: "Cadence weight" }),
  ).toHaveValue("0.8");
  await expect(
    page.locator(".axis-card").first().getByText("80% weight"),
  ).toBeVisible();
  await expect(page.getByTestId("overall-score")).not.toHaveText(
    scoreBefore ?? "",
  );
  await page.getByRole("button", { name: "Close rubric" }).click();
  await page.getByRole("tab", { name: "Acoustic features" }).click();
  await expect(page.locator(".uplot")).toBeVisible();
  await page.getByRole("tab", { name: "Pitch", exact: true }).click();
  await page.locator(".u-over").click({ position: { x: 80, y: 60 } });
  await expect(
    page.getByRole("slider", { name: "Playback position" }),
  ).not.toHaveValue("0");
  await page.getByRole("tab", { name: "Transcript", exact: true }).click();
  await page
    .getByRole("textbox", { name: "Find in transcript" })
    .fill("golden");
  await page.getByRole("textbox", { name: "Find in transcript" }).fill("like");
  await expect(page.locator(".search-match")).not.toHaveCount(0);
  await page.screenshot({
    path: testInfo.outputPath("review-desktop.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    page.getByRole("button", { name: "Play audio", exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: testInfo.outputPath("review-mobile.png"),
    fullPage: true,
  });
  const downloadEvent = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export report" }).click();
  expect((await downloadEvent).suggestedFilename()).toBe("speech-review.json");
  expect(errors).toEqual([]);
});

test("a rejected real upload displays an error instead of fixture results", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Add your recording" }).click();
  await page
    .getByLabel("Choose audio recording")
    .setInputFiles({
      name: "invalid.wav",
      mimeType: "audio/wav",
      buffer: Buffer.from("This is not an audio recording."),
    });
  await page
    .getByLabel("The words you spoke")
    .fill("These are the words I spoke.");
  await page
    .getByRole("button", { name: "Analyze recording", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "We couldn't finish this analysis",
  );
  await expect(page.getByTestId("overall-score")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
});

test("library failure remains visible and uploads stay available", async ({
  page,
}) => {
  await page.route("**/api/library", (route) =>
    route.fulfill({
      status: 503,
      json: { detail: "Library temporarily unavailable." },
    }),
  );
  await page.goto("/");
  await expect(page.getByRole("alert")).toContainText(
    "Library temporarily unavailable.",
  );
  await expect(page.locator(".example-card")).toHaveCount(0);
  await page.getByRole("button", { name: "Add your recording" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByLabel("The words you spoke")).toBeEditable();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.setViewportSize({ width: 360, height: 780 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});
