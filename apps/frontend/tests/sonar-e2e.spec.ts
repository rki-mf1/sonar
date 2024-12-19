import { test, expect } from '@playwright/test'

test('has title', async ({ page }) => {
  await page.goto('http://127.0.0.1:8000/')

  // Expect a title "to contain" a substring.
  await expect(page).toHaveTitle(/Sonar/)
})

test('correct total samples', async ({ page }) => {
  await page.goto('http://127.0.0.1:8000/')

  // Check that the total number of sequences is correct
  await expect(page.getByText('Total: 15 Samples')).toBeVisible()
})
