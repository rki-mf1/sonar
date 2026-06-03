import { test, expect } from '@playwright/test'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const referencePath = '/table?reference_accession=MN908947.3'
const productVersion = readFileSync(
  fileURLToPath(new URL('../../../VERSION', import.meta.url)),
  'utf8',
).trim()

test('has title', async ({ page }) => {
  await page.goto(referencePath)

  // Expect a title "to contain" a substring.
  await expect(page).toHaveTitle(/Sonar/)
})

test('shows product version footer', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByTestId('app-version-footer')).toHaveText(`Sonar v${productVersion}`)
})

test('correct total samples', async ({ page }) => {
  await Promise.all([
    page.waitForResponse(
      (response) => response.url().includes('/api/statistics/') && response.ok(),
      { timeout: 15000 },
    ),
    page.waitForResponse(
      (response) => response.url().includes('/api/samples/genomes/') && response.ok(),
      { timeout: 15000 },
    ),
    page.goto(referencePath),
  ])

  // PrimeVue's footer text is not exposed reliably as one exact text node in Firefox.
  await expect(page.getByText('Samples selected from database')).toBeVisible({ timeout: 15000 })
  const footer = page.locator('.p-datatable-footer')
  await expect(footer).toContainText('Total:', { timeout: 15000 })
  await expect(footer).toContainText('Samples', { timeout: 15000 })
  await expect(footer).toContainText('10', { timeout: 15000 })
})
