import * as v from 'valibot'

export const cardDetailsSchema = v.pipe(
  v.object({
    number: v.pipe(
      v.string(),
      v.transform((val) => val.replace(/\s+/g, '')),
      v.nonEmpty('Номер карты не может быть пустым'),
    ),
    month: v.pipe(
      v.number('Месяц должен быть в диапазоне 1..12'),
      v.minValue(1, 'Месяц должен быть в диапазоне 1..12'),
      v.maxValue(12, 'Месяц должен быть в диапазоне 1..12'),
    ),
    year: v.pipe(
      v.number('Год должен быть от текущего года до +25 лет'),
      v.check((val) => {
        const currentYear = new Date().getFullYear()
        return val >= currentYear && val <= currentYear + 25
      }, 'Год должен быть от текущего года до +25 лет'),
    ),
    cvv: v.pipe(
      v.union([v.string(), v.number()]),
      v.transform((val) => String(val).trim()),
      v.regex(/^\d{3}$/, 'CVV должен состоять ровно из 3 цифр'),
    ),
  }),
  v.check((data) => {
    const now = new Date()
    const currentYear = now.getFullYear()
    const currentMonth = now.getMonth() + 1

    if (data.year < currentYear || (data.year === currentYear && data.month < currentMonth)) {
      return false
    }
    return true
  }, 'Карта просрочена'),
)

export type CardDetailsSchema = v.InferOutput<typeof cardDetailsSchema>
