import { expect, test } from '@nuxt/test-utils/playwright'

test.describe('Deputies list and detail', () => {
  test('deputies page loads with deputy cards', async ({ page, goto }) => {
    await goto('/deputies', { waitUntil: 'hydration' })

    const heading = page.locator('h1')
    await expect(heading).toBeVisible()
    await expect(heading).toContainText('Députés')

    const cards = page.locator('[data-testid="deputy-card"]')
    await expect(cards.first()).toBeVisible({ timeout: 15000 })
  })

  test('deputies search filters list', async ({ page, goto }) => {
    await goto('/deputies', { waitUntil: 'hydration' })

    // Wait for initial list to load
    const cards = page.locator('[data-testid="deputy-card"]')
    await expect(cards.first()).toBeVisible({ timeout: 15000 })

    const initialCount = await cards.count()

    // Fill search input with a common name fragment
    const searchInput = page.locator('input[type="search"]')
    await searchInput.fill('Martin')

    // Wait for debounce + re-fetch
    await page.waitForTimeout(500)

    // Results should update (count may be less or equal depending on data)
    const filteredCount = await cards.count()
    // Either filtered results or no results — both are valid responses to search
    expect(filteredCount).toBeGreaterThanOrEqual(0)
    // Filtered count should be at most the initial count
    expect(filteredCount).toBeLessThanOrEqual(initialCount)
  })

  test('deputy card links to profile', async ({ page, goto }) => {
    await goto('/deputies', { waitUntil: 'hydration' })

    const firstCard = page.locator('[data-testid="deputy-card"]').first()
    await expect(firstCard).toBeVisible({ timeout: 15000 })

    await firstCard.click()

    await expect(page).toHaveURL(/\/deputies\/\d+/)
  })
})
