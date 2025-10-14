import * as v from 'valibot'

export const username = () =>
  v.pipe(
    v.string('должно быть строкой'),
    v.minLength(5, 'должно содержать минимум 5 символов'),
    v.maxLength(32, 'должно содержать не более 32 символов'),
    v.regex(/^[a-zA-Z0-9_]+$/, 'только латинские буквы, цифры и символ "_"'),
    v.check((input: string) => !input.startsWith('_'), 'не может начинаться с "_"'),
    v.check((input: string) => !input.startsWith('_'), 'не может заканчиваться на "_"'),
    v.check((input: string) => !input.includes('__'), 'не может содержать подряд два символа "_"'),
  )

export const photo = () =>
  v.pipeAsync(
    v.file('выберите картинку'),
    v.mimeType(['image/png', 'image/jpeg'], 'выберите JPG или PNG'),
    v.maxSize(1024 * 1024 * 2, 'файл должен быть не больше 2MB'),
    v.checkAsync(async (input: File) => {
      const img = await new Promise<HTMLImageElement>((resolve, reject) => {
        const url = URL.createObjectURL(input)
        const image = new Image()
        image.onload = () => {
          URL.revokeObjectURL(url)
          resolve(image)
        }
        image.onerror = reject
        image.src = url
      })
      return img.width >= 512 && img.height >= 512
    }, 'минимум 512x512 пикселей'),
  )
