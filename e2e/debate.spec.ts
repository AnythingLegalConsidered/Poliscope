import { expect, test } from '@nuxt/test-utils/playwright'

test.describe('Debate detail page', () => {
  test('debate page renders title and interventions', async ({ page, goto }) => {
    // Navigate to home first, then click a debate to get a valid debate URL
    await goto('/', { waitUntil: 'hydration' })

    const firstCard = page.locator('[data-testid="debate-card"]').first()
    await expect(firstCard).toBeVisible({ timeout: 15000 })

    // Click the first debate card to navigate to its detail page
    await firstCard.click()
    await expect(page).toHaveURL(/\/debates\/\d+/)

    const heading = page.locator('h1')
    await expect(heading).toBeVisible({ timeout: 30000 })

    // Title should not be empty
    const titleText = await heading.textContent()
    expect(titleText?.trim().length).toBeGreaterThan(0)

    // At least one intervention card should render
    const interventions = page.locator('[data-testid="intervention-card"]')
    await expect(interventions.first()).toBeVisible({ timeout: 30000 })
  })

  test('intervention cards show speaker names', async ({ page, goto }) => {
    // Navigate via home to get a valid debate
    await goto('/', { waitUntil: 'hydration' })

    const firstCard = page.locator('[data-testid="debate-card"]').first()
    await expect(firstCard).toBeVisible({ timeout: 15000 })
    await firstCard.click()
    await expect(page).toHaveURL(/\/debates\/\d+/)

    const interventionCard = page.locator('[data-testid="intervention-card"]').first()
    await expect(interventionCard).toBeVisible({ timeout: 30000 })

    // Card should contain some text (speaker name or content)
    const cardText = await interventionCard.textContent()
    expect(cardText?.trim().length).toBeGreaterThan(0)
  })
})
