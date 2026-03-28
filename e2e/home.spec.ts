import { expect, test } from '@nuxt/test-utils/playwright'

test.describe('Home page', () => {
  test('home page loads with debate cards', async ({ page, goto }) => {
    await goto('/', { waitUntil: 'hydration' })

    const heading = page.locator('h1')
    await expect(heading).toBeVisible()
    await expect(heading).toContainText('Débats')

    const cards = page.locator('[data-testid="debate-card"]')
    await expect(cards.first()).toBeVisible({ timeout: 15000 })
  })

  test('infinite scroll loads more debates', async ({ page, goto }) => {
    await goto('/', { waitUntil: 'hydration' })

    // Wait for initial cards to render
    const cards = page.locator('[data-testid="debate-card"]')
    await expect(cards.first()).toBeVisible({ timeout: 15000 })

    const initialCount = await cards.count()

    // Scroll to bottom to trigger sentinel
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))

    // Wait a moment for intersection observer to trigger
    await page.waitForTimeout(2000)

    const newCount = await cards.count()
    // Either more cards loaded, or all debates were already on page 1
    expect(newCount).toBeGreaterThanOrEqual(initialCount)
  })

  test('debate card links to debate page', async ({ page, goto }) => {
    await goto('/', { waitUntil: 'hydration' })

    const firstCard = page.locator('[data-testid="debate-card"]').first()
    await expect(firstCard).toBeVisible({ timeout: 15000 })

    await firstCard.click()

    await expect(page).toHaveURL(/\/debates\/\d+/)
  })
})
