import fs from "fs";
import yaml from "js-yaml";
import path from "path";
import { fileURLToPath } from "url";

// ES-модульный аналог __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Пути
const configFile = path.resolve(__dirname, "../config.yml");
const envFile = path.resolve(__dirname, "../.env");

// Читаем YAML
const config = yaml.load(fs.readFileSync(configFile, "utf8"));

// Генерим .env
let envContent = "";
if (config.vite?.api_url) {
  envContent += `API_URL=${config.vite.api_url}\n`;
}

fs.writeFileSync(envFile, envContent);
console.log(".env сгенерирован из config.yml");
