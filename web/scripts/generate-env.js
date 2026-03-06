import fs from 'fs'
import yaml from 'js-yaml'
import path from 'path'
import { fileURLToPath } from 'url'

// ES-модульный аналог __dirname
const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

// Пути
const configFile = path.resolve(__dirname, '../config.yml')
const envFile = path.resolve(__dirname, '../.env')

if (!fs.existsSync(configFile)) {
  throw new Error(`config.yml не найден по пути ${configFile}`)
}

// Читаем YAML
const config = yaml.load(fs.readFileSync(configFile, 'utf8'))

console.log(config)
// Генерим .env
let envContent = ''
if (config.api?.url) {
  envContent += `API_URL=${config.api.url}\n`
}
const usersUrl = config.users?.url || config.neurousers?.url
if (usersUrl) {
  envContent += `USERS_URL=${usersUrl}\n`
}
if (config.api?.bot?.name) {
  envContent += `BOT_NAME=${config.api.bot.name}\n`
}
if (config.web?.url) {
  envContent += `WEB_URL=${config.web.url}\n`
}

fs.writeFileSync(envFile, envContent)
console.log(envContent)
console.log('.env сгенерирован из config.yml')
