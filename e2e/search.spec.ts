import { expect, test } from '@nuxt/test-utils/playwright'

test.describe('Search flow', () => {
  test('header search bar navigates to search page', async ({ page, goto }) => {
    await goto('/', { waitUntil: 'hydration' })

    // Fill the header search input and submit
    const headerInput = page.locator('header input[type="search"]')
    await expect(headerInput).toBeVisible()
    await headerInput.fill('budget')
    await headerInput.press('Enter')

    // Should navigate to /search?q=budget
    await expect(page).toHaveURL(/\/search\?q=budget/)
  })

  test('search results page shows results', async ({ page, goto }) => {
    await goto('/search?q=assemblee', { waitUntil: 'hydration' })

    // Wait for results to render (query triggers on load)
    const resultCards = page.locator('[data-testid="search-result-card"]')
    await expect(resultCards.first()).toBeVisible({ timeout: 20000 })

    const count = await resultCards.count()
    expect(count).toBeGreaterThan(0)
  })

  test('search with no results shows empty state', async ({ page, goto }) => {
    await goto('/search?q=xyznonexistent123', { waitUntil: 'hydration' })

    // Wait for fetch to complete
    await page.waitForTimeout(3000)

    // No result cards should be visible
    const resultCards = page.locator('[data-testid="search-result-card"]')
    const count = await resultCards.count()
    expect(count).toBe(0)

    // Empty state message should appear
    const emptyState = page.locator('text=Aucun résultat')
    await expect(emptyState).toBeVisible({ timeout: 10000 })
  })
})
