<template>
  <div class="flex-1 w-full">
    <div v-if="photos.length">
      <UCarousel
        class="w-full max-w-xs mx-auto"
        ref="carousel"
        v-slot="{ item }"
        arrows
        :items="photos.map((p) => p.url)"
        :prev="{ onClick: prev }"
        :next="{ onClick: next }"
        @select="select"
      >
        <img :src="item" width="320" height="320" class="rounded-lg" />
      </UCarousel>

      <div class="mt-4 max-w-xs mx-auto grid grid-cols-3 gap-2">
        <div v-for="(photo, index) in photos" :key="photo.id" class="relative">
          <img
            :src="photo.url"
            class="w-full h-20 object-cover rounded-lg cursor-pointer"
            :class="{ 'border-2 border-red-500': photo.markedForDeletion }"
            @click="select(index)"
          />

          <UButton
            variant="ghost"
            @click.stop="toggleDelete(photo, index)"
            class="text-red-500 absolute top-0 right-0 w-5 h-5 flex items-center justify-center"
            icon="i-lucide-x"
          />
        </div>
      </div>
    </div>
    <div v-else>
      <UCard>нет фото</UCard>
    </div>

    <div class="mt-4 w-full max-w-xs mx-auto">
      <UButton icon="i-lucide-upload" label="Загрузить" @click="onUploadClick" />
      <input
        type="file"
        multiple="false"
        accept="image/*"
        class="hidden"
        ref="fileInput"
        @change="onFileSelected"
      />
    </div>
    <p v-if="errorMessage" class="text-red-500 text-sm w-full max-w-xs mx-auto mt-2">
      {{ errorMessage }}
    </p>
  </div>
</template>
<script setup lang="ts">
import * as v from 'valibot'
import { ref, watch, defineExpose, useTemplateRef, computed } from 'vue'
import { telegramPhoto } from '@/schemas/validators'

const props = defineProps<{ modelValue: EditableAccountPhoto[] }>()
const emit = defineEmits<{ (e: 'update:modelValue', value: EditableAccountPhoto[]): void }>()

const errorMessage = ref<string | null>(null)
// Фотогалерея
const photos = ref([...props.modelValue])
const carousel = useTemplateRef('carousel')

const fileInput = ref<HTMLInputElement | null>(null)

function onUploadClick() {
  fileInput.value?.click()
}

// Индекс активного слайда
const activeIndex = ref(0)

// Вычисляем активное фото
const activePhoto = computed(() => photos.value[activeIndex.value] || null)

// Отрицательные id для новых файлов
let tempIdCounter = -1

// Синхронизация с родителем через v-model
watch(photos, () => emit('update:modelValue', photos.value), { deep: true })

function select(index: number) {
  activeIndex.value = index

  carousel.value?.emblaApi?.scrollTo(index)
}

function prev() {
  if (activeIndex.value > 0) activeIndex.value--
}

function next() {
  if (activeIndex.value < photos.value.length - 1) activeIndex.value++
}

async function addFile(file: File) {
  errorMessage.value = null
  try {
    await v.parseAsync(telegramPhoto(), file)

    const newPhoto: EditableAccountPhoto = {
      id: tempIdCounter--,
      url: URL.createObjectURL(file),
      file,
    }
    photos.value = [newPhoto, ...photos.value]
    activeIndex.value = 0
    carousel.value?.emblaApi?.scrollTo(0)
  } catch (err) {
    if (err instanceof v.ValiError) {
      // берём первую ошибку
      errorMessage.value = err.issues[0]?.message ?? 'Файл не прошёл проверку'
    } else {
      errorMessage.value = 'Неизвестная ошибка при валидации файла'
    }
  }
}

// Input type="file"
function onFileSelected(event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files || !input.files.length) return
  addFile(input.files[0])
}

function toggleDelete(photo: EditableAccountPhoto, index: number) {
  if (photo.file) {
    // фото только что добавлено → удаляем из массива
    photos.value.splice(index, 1)
    if (activeIndex.value >= photos.value.length) activeIndex.value = photos.value.length - 1
  } else {
    // фото с сервера → просто помечаем/снимаем пометку
    photo.markedForDeletion = !photo.markedForDeletion
  }
}

// Экспорт методов наружу
defineExpose({
  addFile,
  removePhoto(id: number) {
    photos.value = photos.value.filter((p) => p.id !== id)
    if (activeIndex.value >= photos.value.length) activeIndex.value = photos.value.length - 1
  },
  photos,
  activePhoto,
  carousel,
  activeIndex,
})
</script>
