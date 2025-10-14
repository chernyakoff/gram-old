import type { PromptIn } from '@/types/openapi'
import * as v from 'valibot'

const nonEmpty = v.pipe(v.string(), v.nonEmpty('Заполните поле'))

const baseFields = {
  name: nonEmpty,
  role: nonEmpty,
  instruction: nonEmpty,
  context: nonEmpty,
  examples: nonEmpty,
  constraints: nonEmpty,
  outputFormat: nonEmpty,
}

export const promptFormSchema = v.object({
  projectId: v.pipe(
    v.optional(v.number(), undefined),
    v.check((val) => val !== undefined, 'Нужно выбрать проект'),
  ),
  ...baseFields,
})

export type PromptFormSchema = v.InferOutput<typeof promptFormSchema>

const promptInShema = v.object({
  projectId: v.number(),
  ...baseFields,
}) as v.GenericSchema<PromptIn>

export const parsePromptIn = (data: PromptFormSchema) => {
  return v.parse(promptInShema, data) as PromptIn
}
