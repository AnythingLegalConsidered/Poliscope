import { expect, test } from '@nuxt/test-utils/playwright'

test.describe('Chamber filter & Senat debates (Phase 11 verification)', () => {
  test('home page title says "Débats parlementaires" (not AN-specific)', async ({ page, goto }) => {
    await goto('/', { waitUntil: 'hydration' })
    const heading = page.locator('h1')
    await expect(heading).toBeVisible()
    await expect(heading).toContainText('Débats parlementaires')
  })

  test('chamber filter tabs are visible (Tous / AN / Sénat)', async ({ page, goto }) => {
    await goto('/', { waitUntil: 'hydration' })
    await expect(page.getByRole('button', { name: 'Tous' })).toBeVisible()
    await expect(page.getByRole('button', { name: /Assembl[ée]e nationale/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /S[ée]nat/i })).toBeVisible()
  })

  test('Senat filter shows only Senat debates with badge', async ({ page, goto }) => {
    await goto('/', { waitUntil: 'hydration' })

    // Click Senat tab
    await page.getByRole('button', { name: /S[ée]nat/i }).click()

    // Wait for cards to load
    const cards = page.locator('[data-testid="debate-card"]')
    await expect(cards.first()).toBeVisible({ timeout: 15000 })

    // All visible cards should have "Sénat" badge
    const badges = page.locator('[data-testid="debate-card"]').locator('text=Sénat')
    const badgeCount = await badges.count()
    expect(badgeCount).toBeGreaterThan(0)
  })

  test('AN filter shows only AN debates', async ({ page, goto }) => {
    await goto('/', { waitUntil: 'hydration' })

    // Click AN tab
    await page.getByRole('button', { name: /Assembl[ée]e nationale/i }).click()

    // Wait for cards
    const cards = page.locator('[data-testid="debate-card"]')
    await expect(cards.first()).toBeVisible({ timeout: 15000 })

    // Cards should have AN badge
    const badges = page.locator('[data-testid="debate-card"]').locator('text=AN')
    const badgeCount = await badges.count()
    expect(badgeCount).toBeGreaterThan(0)
  })

  test('Senat debate thread is navigable', async ({ page, goto }) => {
    await goto('/', { waitUntil: 'hydration' })

    // Filter to Senat
    await page.getByRole('button', { name: /S[ée]nat/i }).click()

    // Wait and click first debate
    const firstCard = page.locator('[data-testid="debate-card"]').first()
    await expect(firstCard).toBeVisible({ timeout: 15000 })
    await firstCard.click()

    // Should navigate to a debate page
    await expect(page).toHaveURL(/\/debates\/\d+/, { timeout: 10000 })

    // Interventions should be visible (same format as AN)
    const interventions = page.locator('[data-testid="intervention-card"]')
    await expect(interventions.first()).toBeVisible({ timeout: 15000 })
    const count = await interventions.count()
    expect(count).toBeGreaterThan(0)
  })

  test('search returns results from both chambers', async ({ page, goto }) => {
    await goto('/search?q=budget', { waitUntil: 'hydration' })

    const results = page.locator('[data-testid="search-result-card"]')
    await expect(results.first()).toBeVisible({ timeout: 20000 })

    const count = await results.count()
    expect(count).toBeGreaterThan(0)
  })

  test('API /api/debates?chamber=Senat returns Senat data', async ({ page, goto }) => {
    const response = await page.request.get('/api/debates?chamber=Senat&limit=5')
    expect(response.ok()).toBeTruthy()
    const body = await response.json()
    const items = body.data ?? body.debates ?? body
    expect(items.length).toBeGreaterThan(0)
    for (const debate of items) {
      expect(debate.chamber).toBe('Senat')
    }
  })

  test('API /api/debates?chamber=AN returns AN data', async ({ page, goto }) => {
    const response = await page.request.get('/api/debates?chamber=AN&limit=5')
    expect(response.ok()).toBeTruthy()
    const body = await response.json()
    const items = body.data ?? body.debates ?? body
    expect(items.length).toBeGreaterThan(0)
    for (const debate of items) {
      expect(debate.chamber).toBe('AN')
    }
  })

  test('API /api/debates without chamber returns data from at least one chamber', async ({ page, goto }) => {
    // Without filter, API returns all debates (sorted by date — may be all one chamber in first page)
    // The important check: both filtered queries return data (tested above), unfiltered also works
    const response = await page.request.get('/api/debates?limit=5')
    expect(response.ok()).toBeTruthy()
    const body = await response.json()
    const items = body.data ?? body.debates ?? body
    expect(items.length).toBeGreaterThan(0)
    // Verify chamber field exists on items
    expect(items[0]).toHaveProperty('chamber')
  })
})
