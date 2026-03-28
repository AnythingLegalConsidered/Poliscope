import { expect, test } from '@nuxt/test-utils/playwright'

test.describe('Debate detail page', () => {
  test('debate page renders title and interventions', async ({ page, goto }) => {
    await goto('/debates/1', { waitUntil: 'hydration' })

    const heading = page.locator('h1')
    await expect(heading).toBeVisible({ timeout: 15000 })

    // Title should not be empty
    const titleText = await heading.textContent()
    expect(titleText?.trim().length).toBeGreaterThan(0)

    // At least one intervention card should render
    const interventions = page.locator('[data-testid="intervention-card"]')
    await expect(interventions.first()).toBeVisible({ timeout: 15000 })
  })

  test('intervention cards show speaker names', async ({ page, goto }) => {
    await goto('/debates/1', { waitUntil: 'hydration' })

    const firstCard = page.locator('[data-testid="intervention-card"]').first()
    await expect(firstCard).toBeVisible({ timeout: 15000 })

    // Card should contain some text (speaker name or content)
    const cardText = await firstCard.textContent()
    expect(cardText?.trim().length).toBeGreaterThan(0)
  })
})
