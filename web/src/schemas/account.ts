
import * as v from 'valibot'
import { telegramUsername } from './validators'

/*
 avatar: v.optionalAsync(v.pipeAsync(
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
    }, 'минимум 512x512 пикселей')
  )),
*/

export const accountSchema = v.objectAsync({

  username: v.nullable(telegramUsername()),
  channel: v.nullable(telegramUsername()),
  about: v.nullable(v.pipe(
    v.string('должно быть строкой'),
    v.maxLength(64, 'должно содержать не более 64 символов'),
  )),
  firstName: v.nullable(v.pipe(
    v.string('должно быть строкой'),
    v.maxLength(32, 'должно содержать не более 64 символов'),
  )),
  lastName: v.nullable(v.pipe(
    v.string('должно быть строкой'),
    v.maxLength(32, 'должно содержать не более 64 символов'),
  )),

})

export type AccountSchema = v.InferOutput<typeof accountSchema>

export const getAccountData = async (data: Account): Promise<AccountSchema> => {
  const parsed = await v.parseAsync(accountSchema, data);
  return parsed;
}


export interface AccountUpdatePayload extends AccountSchema {
  photos: {
    upload: string[]
    delete: number[]
  }
}
