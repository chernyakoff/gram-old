<template>
  <div
    :class="[
      'rounded-md overflow-hidden transition-all',
      'border border-gray-300 dark:border-gray-700',
      'flex flex-col',
      isMaximized ? 'fixed inset-0 z-50' : '',
    ]"
    :style="{
      height: isMaximized ? '100vh' : props.minHeight || '400px',
    }"
  >
    <!-- Toolbar -->
    <div class="flex gap-2 p-2 toolbar flex-shrink-0">
      <UButton
        type="button"
        variant="ghost"
        @click="isMaximized = !isMaximized"
        :icon="isMaximized ? 'material-symbols:fullscreen-exit' : 'material-symbols:fullscreen'"
      />
      <UButton
        v-for="btn in toolbar"
        :key="btn.name"
        type="button"
        variant="ghost"
        :icon="btn.icon"
        @click="btn.action()"
        :class="btn.isActive() ? 'bg-gray-300 dark:bg-gray-700' : ''"
      />
    </div>

    <!-- Editor -->
    <div class="flex-1 overflow-auto editor-container">
      <EditorContent :editor="editor" class="h-full prose dark:prose-invert max-w-none" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineProps, watch, onBeforeUnmount } from 'vue'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import HorizontalRule from '@tiptap/extension-horizontal-rule'
import StarterKit from '@tiptap/starter-kit'
import { ref } from 'vue'

const isMaximized = ref(false)

const props = defineProps<{
  modelValue: string
  minHeight?: string
}>()

const editor = useEditor({
  extensions: [StarterKit, HorizontalRule],
  content: props.modelValue || '',
  onUpdate({ editor }) {
    emit('update:modelValue', editor.getHTML())
  },
})

const toolbar = [
  {
    name: 'bold',
    icon: 'material-symbols:format-bold',
    action: () => editor.value?.chain().focus().toggleBold().run(),
    isActive: () => editor.value?.isActive('bold') || false,
  },
  {
    name: 'italic',
    icon: 'material-symbols:format-italic',
    action: () => editor.value?.chain().focus().toggleItalic().run(),
    isActive: () => editor.value?.isActive('italic') || false,
  },
  {
    name: 'h1',
    icon: 'material-symbols:format-h1',
    action: () => editor.value?.chain().focus().toggleHeading({ level: 1 }).run(),
    isActive: () => editor.value?.isActive('heading', { level: 1 }) || false,
  },
  {
    name: 'h2',
    icon: 'material-symbols:format-h2',
    action: () => editor.value?.chain().focus().toggleHeading({ level: 2 }).run(),
    isActive: () => editor.value?.isActive('heading', { level: 2 }) || false,
  },
  {
    name: 'h3',
    icon: 'material-symbols:format-h3',
    action: () => editor.value?.chain().focus().toggleHeading({ level: 3 }).run(),
    isActive: () => editor.value?.isActive('heading', { level: 3 }) || false,
  },
  {
    name: 'bulletList',
    icon: 'material-symbols:format-list-bulleted',
    action: () => editor.value?.chain().focus().toggleBulletList().run(),
    isActive: () => editor.value?.isActive('bulletList') || false,
  },
  {
    name: 'orderedList',
    icon: 'material-symbols:format-list-numbered',
    action: () => editor.value?.chain().focus().toggleOrderedList().run(),
    isActive: () => editor.value?.isActive('orderedList') || false,
  },
  {
    name: 'hr',
    icon: 'material-symbols:horizontal-rule',
    action: () => editor.value?.chain().focus().setHorizontalRule().run(),
    isActive: () => false,
  },
  {
    name: 'code',
    icon: 'material-symbols:code',
    action: () => editor.value?.chain().focus().toggleCode().run(),
    isActive: () => editor.value?.isActive('code') || false,
  },
  {
    name: 'clear',
    icon: 'material-symbols:ink-eraser',
    action: () => editor.value?.chain().focus().unsetAllMarks().clearNodes().run(),
    isActive: () => false,
  },
]

watch(
  () => props.modelValue,
  (val) => {
    if (editor.value && val !== editor.value.getHTML()) {
      editor.value.commands.setContent(val)
    }
  },
)

onBeforeUnmount(() => editor.value?.destroy())

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()
</script>

<style scoped>
.toolbar {
  background-color: rgb(168, 168, 168);
}

.dark .toolbar {
  background-color: #313233;
}

.editor-container {
  background-color: white;
}

.dark .editor-container {
  background-color: #1e1f20;
}
</style>

<style>
/* Глобальные стили для ProseMirror */
.ProseMirror {
  padding: 0.75rem;
  min-height: 100%;
  outline: none;
  background-color: transparent;
  color: #1f2937;
}

.dark .ProseMirror {
  color: #e5e7eb;
}

.ProseMirror h1 {
  font-size: 1.875rem;
  font-weight: 700;
  margin-bottom: 0.75rem;
  margin-top: 0.75rem;
}

.ProseMirror h2 {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  margin-top: 0.5rem;
}

.ProseMirror h3 {
  font-size: 1.25rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  margin-top: 0.5rem;
}

.ProseMirror p {
  margin-bottom: 0.5rem;
}

.ProseMirror hr {
  border-top: 1px solid #d1d5db;
  margin: 1rem 0;
}

.dark .ProseMirror hr {
  border-top-color: #4b5563;
}

.ProseMirror ul {
  padding-left: 1.5rem;
  list-style-type: disc;
  margin-bottom: 0.5rem;
}

.ProseMirror ol {
  padding-left: 1.5rem;
  list-style-type: decimal;
  margin-bottom: 0.5rem;
}

.ProseMirror li {
  margin-bottom: 0.25rem;
}

.ProseMirror code {
  font-family: monospace;
  background-color: #f3f4f6;
  padding: 0.125rem 0.25rem;
  border-radius: 0.25rem;
  font-size: 0.875em;
}

.dark .ProseMirror code {
  background-color: #374151;
  color: #f9fafb;
}

.ProseMirror:focus {
  outline: none;
}
</style>
