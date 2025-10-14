<template>
  <div class="flex-1 w-full">
    <div v-if="editor.photos.length" class="space-y-4">
      <!-- Основная карусель -->
      <UCarousel
        ref="carouselRef"
        class="w-full max-w-xs mx-auto"
        v-slot="{ item }"
        arrows
        :items="editor.photos.map((p: EditableAccountPhoto) => p.url)"
        @select="activeIndex = $event"
      >
        <img :src="item as string" width="320" height="320" class="rounded-lg" />
      </UCarousel>

      <!-- Миниатюры -->
      <div class="max-w-xs mx-auto grid grid-cols-3 gap-2">
        <div v-for="(photo, index) in editor.photos" :key="photo.id" class="relative group">
          <img
            :src="photo.url"
            class="w-full h-20 object-cover rounded-lg cursor-pointer transition"
            :class="{
              'border-2 border-red-500': photo.markedForDeletion,
              'ring-2 ring-primary': index === activeIndex,
            }"
            @click="selectPhoto(index)"
          />

          <UButton
            variant="ghost"
            size="xs"
            icon="i-lucide-x"
            class="absolute top-1 right-1 opacity-0 group-hover:opacity-100 transition"
            @click.stop="onDeleteClick(index)"
          />
        </div>
      </div>
    </div>

    <!-- Пустое состояние -->
    <div v-else class="text-center py-8 text-gray-500">Нет фото</div>

    <!-- Загрузка фото -->
    <div class="mt-4 w-full max-w-xs mx-auto">
      <UButton icon="i-lucide-upload" label="Загрузить фото" block @click="fileInput?.click()" />
      <input ref="fileInput" type="file" accept="image/*" class="hidden" @change="onFileChange" />

      <p v-if="error" class="text-red-500 text-sm mt-2">
        {{ error }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import * as v from 'valibot'
import { ref } from 'vue'
import { photo as telegramPhoto } from '@/schemas/atoms/telegram'
import { useAccountEditor } from '@/stores/account-store'
import type { EditableAccountPhoto } from '@/schemas/accounts'

const editor = useAccountEditor()

const carouselRef = ref()
const fileInput = ref<HTMLInputElement>()
const activeIndex = ref(0)
const error = ref<string>()

function selectPhoto(index: number) {
  activeIndex.value = index
  carouselRef.value?.emblaApi?.scrollTo(index)
}

async function onFileChange(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return

  error.value = undefined

  try {
    // Валидация файла
    await v.parseAsync(telegramPhoto(), file)
    editor.addPhoto(file)
    selectPhoto(0)
  } catch (err) {
    if (err instanceof v.ValiError) {
      error.value = err.issues[0]?.message ?? 'Файл не прошёл проверку'
    } else {
      error.value = 'Ошибка при валидации файла'
    }
  }

  // Сброс input
  if (fileInput.value) fileInput.value.value = ''
}

function onDeleteClick(index: number) {
  editor.togglePhotoDelete(index)
  if (activeIndex.value >= editor.photos.length) {
    activeIndex.value = Math.max(0, editor.photos.length - 1)
  }
}
</script>
