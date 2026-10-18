import { mkdir, readFile, rename, rm } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { spawnSync } from 'node:child_process'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright-core'

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const baseUrl = process.env.BASE_URL || 'http://localhost:3000'
const chromePath =
  process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
const videoDir = resolve(projectRoot, 'out/demo/headless-video')
const webmPath = resolve(projectRoot, 'out/demo/analysis-editor-headless.webm')
const outputPath = resolve(projectRoot, 'out/demo/analysis-editor-headless.mp4')
const fixtureDir = resolve(projectRoot, 'e2e/ui/src/test/resources/common/data/generated')

async function requestJson(path, options) {
  const response = await fetch(new URL(path, baseUrl), options)
  if (!response.ok) {
    throw new Error(
      `${options?.method ?? 'GET'} ${path} returned ${response.status}: ${await response.text()}`,
    )
  }
  return response.status === 204 ? null : response.json()
}

async function createCompletedAnalysis(filename, documentIds) {
  const bytes = await readFile(resolve(fixtureDir, filename))
  const form = new FormData()
  form.set('file', new File([bytes], filename, { type: 'application/pdf' }))
  const uploaded = await requestJson('/api/documents/upload', { method: 'POST', body: form })
  documentIds.push(uploaded.id)

  const analysis = await requestJson('/api/analyses', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ documentId: uploaded.id }),
  })
  let status = analysis.status
  for (let attempt = 0; attempt < 180 && status !== 'COMPLETED' && status !== 'FAILED'; attempt++) {
    await new Promise((resolveWait) => setTimeout(resolveWait, 2000))
    status = (await requestJson(`/api/analyses/${analysis.id}`)).status
  }
  if (status !== 'COMPLETED') throw new Error(`${filename} analysis failed (status: ${status})`)
  return analysis.id
}

async function pause(page, milliseconds = 900) {
  await page.waitForTimeout(milliseconds)
}

async function openEditor(page, analysisId) {
  await page.goto(new URL(`/analyses/${analysisId}`, baseUrl).toString())
  await page.locator('[data-e2e=analysis-edit-toggle]').click()
  await page.locator('[data-editor=analysis-editor]').waitFor()
}

async function showMarkdown(page) {
  await page.locator('[data-e2e=analysis-editor-markdown-tab]').click()
  await page.locator('[data-e2e=analysis-editor-markdown]').waitFor()
}

async function saveAndWait(page) {
  await page.locator('[data-e2e=analysis-editor-save]').click()
  await page.locator('[data-e2e=analysis-editor-saved]').waitFor()
  await pause(page, 900)
}

async function waitForMarkdown(page, predicate) {
  await page.waitForFunction(predicate)
}

await mkdir(videoDir, { recursive: true })
await rm(webmPath, { force: true })
await rm(outputPath, { force: true })

const documentIds = []
let context
let browser
let video
let testError

try {
  const textAnalysisId = await createCompletedAnalysis('editor-text.pdf', documentIds)
  const structureAnalysisId = await createCompletedAnalysis('editor-structure.pdf', documentIds)

  browser = await chromium.launch({ headless: true, executablePath: chromePath })
  context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    recordVideo: { dir: videoDir, size: { width: 1440, height: 900 } },
  })
  const page = await context.newPage()
  video = page.video()
  page.on('dialog', (dialog) => dialog.accept())

  // Replace a paragraph, save it, and show that the edit survives a reload.
  await openEditor(page, textAnalysisId)
  await pause(page)
  await page.locator('[data-e2e=analysis-editor-tree-item-editor-alpha-paragraph-marker]').click()
  await page.locator('[data-e2e=analysis-editor-text]').fill('Editor alpha revised marker.')
  await page.locator('[data-e2e=analysis-editor-unsaved]').waitFor()
  await showMarkdown(page)
  await page.locator('[data-e2e=analysis-editor-undo]').click()
  await waitForMarkdown(page, () => {
    const markdown = document.querySelector('[data-e2e=analysis-editor-markdown]')?.textContent ?? ''
    return markdown.includes('Editor alpha paragraph marker.') && !markdown.includes('Editor alpha revised marker.')
  })
  await page.locator('[data-e2e=analysis-editor-redo]').click()
  await waitForMarkdown(page, () =>
    document.querySelector('[data-e2e=analysis-editor-markdown]')?.textContent.includes(
      'Editor alpha revised marker.',
    ),
  )
  await pause(page, 700)
  await pause(page)
  await saveAndWait(page)
  await page.reload()
  await openEditor(page, textAnalysisId)
  await page.locator('[data-e2e=analysis-editor-tree-item-editor-alpha-revised-marker]').click()
  if ((await page.locator('[data-e2e=analysis-editor-text]').inputValue()) !== 'Editor alpha revised marker.') {
    throw new Error('Text replacement did not survive reload')
  }
  await showMarkdown(page)
  await waitForMarkdown(page, () =>
    document.querySelector('[data-e2e=analysis-editor-markdown]')?.textContent.includes(
      'Editor alpha revised marker.',
    ),
  )
  await pause(page, 1000)

  // Merge two paragraphs, persist, reload, and show the merged projection.
  await page
    .locator('[data-e2e=analysis-editor-item-editor-alpha-revised-marker] [data-e2e=analysis-editor-merge-select]')
    .click()
  await page
    .locator('[data-e2e=analysis-editor-item-editor-bravo-paragraph-marker] [data-e2e=analysis-editor-merge-select]')
    .click()
  await page.locator('[data-e2e=analysis-editor-merge]').click()
  await page.locator('[data-e2e=analysis-editor-unsaved]').waitFor()
  await saveAndWait(page)
  await page.reload()
  await openEditor(page, textAnalysisId)
  await showMarkdown(page)
  await waitForMarkdown(page, () =>
    document.querySelector('[data-e2e=analysis-editor-markdown]')?.textContent.includes(
      'Editor alpha revised marker. Editor bravo paragraph marker.',
    ),
  )
  await pause(page, 1000)

  // Confirm and persist a range deletion.
  await page
    .locator('[data-e2e=analysis-editor-item-editor-charlie-paragraph-marker] [data-e2e=analysis-editor-merge-select]')
    .click()
  await page
    .locator('[data-e2e=analysis-editor-item-editor-delta-paragraph-marker] [data-e2e=analysis-editor-merge-select]')
    .click()
  await page.locator('[data-e2e=analysis-editor-delete-range]').click()
  await page.locator('[data-e2e=analysis-editor-unsaved]').waitFor()
  await saveAndWait(page)
  await page.reload()
  await openEditor(page, textAnalysisId)
  await showMarkdown(page)
  await waitForMarkdown(page, () => {
    const markdown = document.querySelector('[data-e2e=analysis-editor-markdown]')?.textContent ?? ''
    return !markdown.includes('Editor charlie paragraph marker.') && !markdown.includes('Editor delta paragraph marker.')
  })
  await pause(page, 1000)

  // Discard a local draft and return to the saved text.
  await page.locator('[data-e2e=analysis-editor-tree-item-text-section-alpha]').click()
  await page.locator('[data-e2e=analysis-editor-text]').fill('This local edit will be discarded.')
  await page.locator('[data-e2e=analysis-editor-unsaved]').waitFor()
  await page.locator('[data-e2e=analysis-editor-discard]').click()
  await showMarkdown(page)
  await waitForMarkdown(page, () =>
    document.querySelector('[data-e2e=analysis-editor-markdown]')?.textContent.includes(
      'Editor alpha revised marker. Editor bravo paragraph marker.',
    ),
  )
  await pause(page, 1000)

  // Move a paragraph into a section, change its heading level, then reload.
  await openEditor(page, structureAnalysisId)
  await page.locator('[data-e2e=analysis-editor-tree-item-structure-one-alpha-paragraph-marker]').click()
  await page.locator('[data-e2e=analysis-editor-choose-move]').click()
  await page
    .locator('[data-e2e=analysis-editor-item-structure-section-two] [data-e2e=analysis-editor-move-inside]')
    .click()
  await page.locator('[data-e2e=analysis-editor-tree-item-structure-section-two]').click()
  await page.locator('[data-e2e=analysis-editor-heading-level]').selectOption('2')
  await page.locator('[data-e2e=analysis-editor-unsaved]').waitFor()
  await saveAndWait(page)
  await page.reload()
  await openEditor(page, structureAnalysisId)
  await showMarkdown(page)
  await waitForMarkdown(page, () => {
    const markdown = document.querySelector('[data-e2e=analysis-editor-markdown]')?.textContent ?? ''
    return (
      markdown.includes('### Structure section two') &&
      markdown.indexOf('### Structure section two') <
        markdown.indexOf('Structure one alpha paragraph marker.')
    )
  })
  await pause(page, 1400)
} catch (error) {
  testError = error
} finally {
  if (context) await context.close()
  if (browser) await browser.close()
  if (video) {
    const recordedPath = await video.path()
    if (existsSync(recordedPath)) {
      await rename(recordedPath, webmPath)
      const conversion = spawnSync(
        'ffmpeg',
        [
          '-y',
          '-loglevel',
          'error',
          '-i',
          webmPath,
          '-c:v',
          'libx264',
          '-pix_fmt',
          'yuv420p',
          '-movflags',
          '+faststart',
          outputPath,
        ],
        { stdio: 'inherit' },
      )
      if (conversion.status !== 0 && !testError) {
        testError = conversion.error ?? new Error('ffmpeg failed to convert the headless recording')
      }
      if (conversion.status === 0) await rm(webmPath, { force: true })
    }
  }
  for (const documentId of documentIds) {
    try {
      await requestJson(`/api/documents/${documentId}`, { method: 'DELETE' })
    } catch (cleanupError) {
      console.warn(`Document cleanup failed for ${documentId}: ${cleanupError.message}`)
    }
  }
}

if (testError) throw testError
console.log(`Headless analysis editor walkthrough video: ${outputPath}`)
