export function generateMessage(template: string): string {
  // Экранированные символы
  const ESCAPES: Record<string, string> = {
    '\\{': '\ue000',
    '\\}': '\ue001',
    '\\|': '\ue002',
    '\\\\': '\ue003',
  }

  // Заменяем экранированные символы на временные метки
  for (const [k, v] of Object.entries(ESCAPES)) {
    template = template.split(k).join(v)
  }

  function expand(text: string): string {
    const stack: number[] = []
    let i = 0

    while (i < text.length) {
      if (text[i] === '{') {
        stack.push(i)
        i++
      } else if (text[i] === '}') {
        if (stack.length > 0) {
          const start = stack.pop()!
          const inner = text.slice(start + 1, i)
          const options = inner.split('|').map((opt) => expand(opt))

          const choice = options[Math.floor(Math.random() * options.length)] ?? ''

          text = text.slice(0, start) + choice + text.slice(i + 1)
          i = start + choice.length
        } else {
          i++
        }
      } else {
        i++
      }
    }

    return text
  }

  let result = expand(template)

  // Возвращаем экранированные символы обратно
  for (const [k, v] of Object.entries(ESCAPES)) {
    switch (k) {
      case '\\\\':
        result = result.split(v).join('\\')
        break
      case '\\{':
        result = result.split(v).join('{')
        break
      case '\\}':
        result = result.split(v).join('}')
        break
      case '\\|':
        result = result.split(v).join('|')
        break
    }
  }

  return result
}
