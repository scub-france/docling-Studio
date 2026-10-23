import { mkdir, readFile, rename, rm } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { spawnSync } from 'node:child_process'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright-core'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const baseUrl = process.env.BASE_URL || 'http://localhost:3000'
const chromePath =
  process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
const fixtureDir = resolve(root, 'e2e/ui/src/test/resources/common/data/generated')
const videoDir = resolve(root, 'out/demo/editor-clips')
const documentIds = []

async function api(path, options = {}) {
  const response = await fetch(new URL(path, baseUrl), options)
  if (!response.ok) {
    throw new Error(`${options.method || 'GET'} ${path}: ${response.status} ${await response.text()}`)
  }
  return response.status === 204 ? null : response.json()
}

async function createAnalysis(filename) {
  const form = new FormData()
  form.set(
    'file',
    new File([await readFile(resolve(fixtureDir, filename))], filename, { type: 'application/pdf' }),
  )
  const document = await api('/api/documents/upload', { method: 'POST', body: form })
  documentIds.push(document.id)
  const analysis = await api('/api/analyses', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ documentId: document.id }),
  })
  let status = analysis.status
  for (let attempt = 0; attempt < 180 && status !== 'COMPLETED' && status !== 'FAILED'; attempt++) {
    await new Promise((resolveWait) => setTimeout(resolveWait, 2000))
    status = (await api(`/api/analyses/${analysis.id}`)).status
  }
  if (status !== 'COMPLETED') throw new Error(`${filename} analysis failed: ${status}`)
  return { documentId: document.id, analysisId: analysis.id }
}

async function waitForMarkdown(page, predicate) {
  await page.waitForFunction(predicate)
}

async function showMarkdown(page) {
  await page.locator('[data-e2e=analysis-editor-markdown-tab]').click()
  await page.locator('[data-e2e=analysis-editor-markdown]').waitFor()
}

async function openEditor(page, analysisId) {
  await page.goto(new URL(`/analyses/${analysisId}`, baseUrl).toString())
  await page.locator('[data-e2e=analysis-edit-toggle]').click()
  await page.locator('[data-editor=analysis-editor]').waitFor()
}

async function save(page) {
  await page.locator('[data-e2e=analysis-editor-save]').click()
  await page.locator('[data-e2e=analysis-editor-saved]').waitFor()
  await page.waitForTimeout(900)
}

async function recordClip(browser, name, workflow) {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    recordVideo: { dir: videoDir, size: { width: 1440, height: 900 } },
  })
  const page = await context.newPage()
  const video = page.video()
  page.on('dialog', (dialog) => dialog.accept())
  let failure
  try {
    await workflow(page)
  } catch (error) {
    failure = error
  } finally {
    await context.close()
    const source = await video.path()
    if (existsSync(source)) {
      const webm = resolve(videoDir, `${name}.webm`)
      const mp4 = resolve(root, 'out/demo', `${name}.mp4`)
      await rm(mp4, { force: true })
      await rename(source, webm)
      const result = spawnSync(
        'ffmpeg',
        ['-y', '-loglevel', 'error', '-i', webm, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', mp4],
        { stdio: 'inherit' },
      )
      if (result.status === 0) {
        await rm(webm, { force: true })
        console.log(`${name}: ${mp4}`)
      } else if (!failure) {
        failure = result.error || new Error(`ffmpeg could not encode ${name}`)
      }
    }
  }
  if (failure) throw failure
}

await mkdir(videoDir, { recursive: true })
const browser = await chromium.launch({ headless: true, executablePath: chromePath })
let textAnalysis
let structureAnalysis
let failure

try {
  textAnalysis = await createAnalysis('editor-text.pdf')
  structureAnalysis = await createAnalysis('editor-structure.pdf')

  await recordClip(browser, 'analysis-editor-text-actions', async (page) => {
    const analysisId = textAnalysis.analysisId
    await openEditor(page, analysisId)
    await page.waitForTimeout(700)

    // Replace text, demonstrate pending undo/redo, then save and reload.
    await page.locator('[data-e2e=analysis-editor-tree-item-editor-alpha-paragraph-marker]').click()
    await page.locator('[data-e2e=analysis-editor-text]').fill('Editor alpha showcase marker.')
    await page.locator('[data-e2e=analysis-editor-unsaved]').waitFor()
    await showMarkdown(page)
    await page.locator('[data-e2e=analysis-editor-undo]').click()
    await waitForMarkdown(page, () => {
      const text = document.querySelector('[data-e2e=analysis-editor-markdown]')?.textContent ?? ''
      return text.includes('Editor alpha paragraph marker.') && !text.includes('Editor alpha showcase marker.')
    })
    await page.waitForTimeout(600)
    await page.locator('[data-e2e=analysis-editor-redo]').click()
    await waitForMarkdown(page, () =>
      document.querySelector('[data-e2e=analysis-editor-markdown]')?.textContent.includes(
        'Editor alpha showcase marker.',
      ),
    )
    await save(page)
    await page.reload()
    await openEditor(page, analysisId)
    await showMarkdown(page)
    await waitForMarkdown(page, () =>
      document.querySelector('[data-e2e=analysis-editor-markdown]')?.textContent.includes(
        'Editor alpha showcase marker.',
      ),
    )
    await page.waitForTimeout(900)

    // Merge adjacent text selections and save the merged projection.
    await page
      .locator('[data-e2e=analysis-editor-item-editor-alpha-showcase-marker] [data-e2e=analysis-editor-merge-select]')
      .click()
    await page
      .locator('[data-e2e=analysis-editor-item-editor-bravo-paragraph-marker] [data-e2e=analysis-editor-merge-select]')
      .click()
    await page.locator('[data-e2e=analysis-editor-merge]').click()
    await page.locator('[data-e2e=analysis-editor-unsaved]').waitFor()
    await save(page)
    await page.reload()
    await openEditor(page, analysisId)
    await showMarkdown(page)
    await waitForMarkdown(page, () =>
      document.querySelector('[data-e2e=analysis-editor-markdown]')?.textContent.includes(
        'Editor alpha showcase marker. Editor bravo paragraph marker.',
      ),
    )
    await page.waitForTimeout(900)

    // Select-range deletion asks for confirmation before queuing the command.
    await page
      .locator('[data-e2e=analysis-editor-item-editor-charlie-paragraph-marker] [data-e2e=analysis-editor-merge-select]')
      .click()
    await page
      .locator('[data-e2e=analysis-editor-item-editor-delta-paragraph-marker] [data-e2e=analysis-editor-merge-select]')
      .click()
    await page.locator('[data-e2e=analysis-editor-delete-range]').click()
    await page.locator('[data-e2e=analysis-editor-unsaved]').waitFor()
    await save(page)
    await page.reload()
    await openEditor(page, analysisId)
    await showMarkdown(page)
    await waitForMarkdown(page, () => {
      const text = document.querySelector('[data-e2e=analysis-editor-markdown]')?.textContent ?? ''
      return !text.includes('Editor charlie paragraph marker.') && !text.includes('Editor delta paragraph marker.')
    })
    await page.waitForTimeout(900)

    // Discard a new local draft and leave the saved projection untouched.
    await page.locator('[data-e2e=analysis-editor-tree-item-text-section-alpha]').click()
    await page.locator('[data-e2e=analysis-editor-text]').fill('This edit is discarded.')
    await page.locator('[data-e2e=analysis-editor-unsaved]').waitFor()
    await page.locator('[data-e2e=analysis-editor-discard]').click()
    await showMarkdown(page)
    await waitForMarkdown(page, () =>
      document.querySelector('[data-e2e=analysis-editor-markdown]')?.textContent.includes(
        'Editor alpha showcase marker. Editor bravo paragraph marker.',
      ),
    )
    await page.waitForTimeout(1200)
  })

  await recordClip(browser, 'analysis-editor-structure-actions', async (page) => {
    const analysisId = structureAnalysis.analysisId
    await openEditor(page, analysisId)
    await page.waitForTimeout(700)

    // Move a paragraph into another section and change that heading's level.
    await page.locator('[data-e2e=analysis-editor-tree-item-structure-one-alpha-paragraph-marker]').click()
    await page.locator('[data-e2e=analysis-editor-choose-move]').click()
    await page
      .locator('[data-e2e=analysis-editor-item-structure-section-two] [data-e2e=analysis-editor-move-inside]')
      .click()
    await page.locator('[data-e2e=analysis-editor-tree-item-structure-section-two]').click()
    await page.locator('[data-e2e=analysis-editor-heading-level]').selectOption('2')
    await page.locator('[data-e2e=analysis-editor-unsaved]').waitFor()
    await page.waitForTimeout(700)
    await save(page)
    await page.reload()
    await openEditor(page, analysisId)
    await showMarkdown(page)
    await waitForMarkdown(page, () => {
      const text = document.querySelector('[data-e2e=analysis-editor-markdown]')?.textContent ?? ''
      return (
        text.includes('### Structure section two') &&
        text.indexOf('### Structure section two') < text.indexOf('Structure one alpha paragraph marker.')
      )
    })
    await page.waitForTimeout(1200)
  })
} catch (error) {
  failure = error
} finally {
  await browser.close()
  for (const item of [textAnalysis, structureAnalysis]) {
    if (!item) continue
    try {
      await api(`/api/documents/${item.documentId}`, { method: 'DELETE' })
    } catch (cleanupError) {
      console.warn(`Document cleanup failed for ${item.documentId}: ${cleanupError.message}`)
    }
  }
}

if (failure) throw failure
console.log('Headless editor action videos recorded.')
