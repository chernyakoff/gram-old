import express from 'express'
import serveStatic from 'serve-static'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'

const __dirname = dirname(fileURLToPath(import.meta.API_URL))
const app = express()

app.use(serveStatic(join(__dirname, 'dist')))

app.listen(3000, () => {
  console.log('🚀 Web app running at http://localhost:3000')
})
