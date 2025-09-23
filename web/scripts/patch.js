import fs from 'fs'
import path from 'path'

const filePath = path.resolve('node_modules/@nuxt/ui-pro/dist/unplugin.mjs')

let code = fs.readFileSync(filePath, 'utf8')

const patched = code.replace(/,\s*LicensePlugin\(options\.license\)/, '')

if (patched !== code) {
  fs.writeFileSync(filePath, patched, 'utf8')
  console.log('✅ LicensePlugin(options.license) убран из @nuxt/ui-pro/dist/unplugin.mjs')
} else {
  console.log('ℹ️ Ничего не поменялось (возможно, строка уже удалена).')
}
