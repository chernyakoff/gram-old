#!/usr/bin/env node

import fs from 'fs/promises'
import path from 'path'
import ts from 'typescript'
import openapiTS from 'openapi-typescript'

function astToString(ast, options) {
  const sourceFile = ts.createSourceFile(
    options?.fileName ?? 'openapi-ts.ts',
    options?.sourceText ?? '',
    ts.ScriptTarget.ESNext,
    false,
    ts.ScriptKind.TS,
  )

  const filterSet = new Set(options?.filterNames ?? [])

  const filteredStatements = (Array.isArray(ast) ? ast : [ast]).filter((node) => {
    if (
      (ts.isInterfaceDeclaration(node) ||
        ts.isTypeAliasDeclaration(node) ||
        ts.isEnumDeclaration(node)) &&
      filterSet.has(node.name?.text)
    )
      return false
    return true
  })

  const updatedSourceFile = ts.factory.updateSourceFile(sourceFile, filteredStatements)

  const printer = ts.createPrinter({
    newLine: ts.NewLineKind.LineFeed,
    removeComments: true,
    ...options?.formatOptions,
  })

  return printer.printFile(updatedSourceFile)
}

function toCamelCase(str) {
  return str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase())
}

function transformSchema(schema) {
  if (!schema) return schema
  if (schema.type === 'object' && schema.properties) {
    const newProps = {}
    for (const [key, value] of Object.entries(schema.properties)) {
      newProps[toCamelCase(key)] = transformSchema(value)
    }
    schema.properties = newProps
  }
  if (Array.isArray(schema.required)) {
    schema.required = schema.required.map(toCamelCase)
  }
  if (schema.type === 'array' && schema.items) {
    schema.items = transformSchema(schema.items)
  }
  return schema
}

function camelCaseTransform(schema) {
  transformSchema(schema)
  return undefined
}

async function generateOpenapi(input, output) {
  try {
    let tsNodes

    if (input.startsWith('http://') || input.startsWith('https://')) {
      tsNodes = await openapiTS(input, {
        rootTypes: true,
        rootTypesNoSchemaPrefix: true,
        transform: camelCaseTransform,
      })
    } else {
      const resolvedPath = path.resolve(process.cwd(), input)
      const raw = await fs.readFile(resolvedPath, 'utf-8')
      const openapi = JSON.parse(raw)
      tsNodes = await openapiTS(openapi, {
        rootTypes: true,
        rootTypesNoSchemaPrefix: true,
        transform: camelCaseTransform,
      })
    }

    const tsCode = astToString(tsNodes, {
      filterNames: ['paths', 'operations', '$defs', 'webhooks'],
    })

    const resolvedOutput = path.resolve(process.cwd(), output)
    const outputDir = path.dirname(resolvedOutput)
    await fs.mkdir(outputDir, { recursive: true })

    await fs.writeFile(resolvedOutput, tsCode, 'utf-8')
    console.log(`✅ Создан ${resolvedOutput}`)
  } catch (err) {
    console.error('Ошибка генерации openapi.ts:', err)
    process.exit(1)
  }
}

// читаем аргументы
const [, , input, output] = process.argv

if (!input || !output) {
  console.error('Использование: node generate-openapi.js <путь_или_URL> <путь_для_вывода>')
  process.exit(1)
}

;(async () => {
  await generateOpenapi(input, output)
})()
