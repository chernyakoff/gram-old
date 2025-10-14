import { camelCase, snakeCase } from 'scule'

type PlainObject = { [key: string]: unknown }

export function keysToCamel<T>(obj: T): T {
  if (Array.isArray(obj)) {
    return obj.map((v) => keysToCamel(v)) as unknown as T
  } else if (obj !== null && typeof obj === 'object') {
    const result: PlainObject = {}
    Object.keys(obj).forEach((key) => {
      result[camelCase(key)] = keysToCamel((obj as PlainObject)[key])
    })
    return result as T
  }
  return obj
}

export function keysToSnake<T>(obj: T): T {
  if (Array.isArray(obj)) {
    return obj.map((v) => keysToSnake(v)) as unknown as T
  } else if (obj !== null && typeof obj === 'object') {
    const result: PlainObject = {}
    Object.keys(obj).forEach((key) => {
      result[snakeCase(key)] = keysToSnake((obj as PlainObject)[key])
    })
    return result as T
  }
  return obj
}
