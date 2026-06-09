<template>
  <div class="composer-container">
    <div class="composer-input-wrapper">
      <div class="search-icon-static">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
          <path d="M21 21L16.65 16.65M19 11C19 15.4183 15.4183 19 11 19C6.58172 19 3 15.4183 3 11C3 6.58172 6.58172 3 11 3C15.4183 3 19 6.58172 19 11Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>
      <textarea
        ref="textareaRef"
        :value="modelValue"
        @input="handleInput"
        class="composer-textarea"
        placeholder="输入主题，例如：秋季显白穿搭、周末探店路线..."
        @keydown.enter.prevent="handleEnter"
        :disabled="loading"
        rows="1"
      ></textarea>
    </div>

    <div v-if="uploadedImages.length > 0" class="uploaded-images-preview">
      <div
        v-for="(img, idx) in uploadedImages"
        :key="idx"
        class="uploaded-image-item"
      >
        <img :src="img.preview" :alt="`参考图 ${idx + 1}`" />
        <button class="remove-image-btn" type="button" @click="removeImage(idx)">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
      <div class="upload-hint">已添加 {{ uploadedImages.length }} 张参考图</div>
    </div>

    <div class="composer-toolbar">
      <label class="tool-btn" :class="{ active: uploadedImages.length > 0 }" title="上传参考图">
        <input
          type="file"
          accept="image/*"
          multiple
          @change="handleImageUpload"
          :disabled="loading"
          style="display: none;"
        />
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
          <circle cx="8.5" cy="8.5" r="1.5"></circle>
          <polyline points="21 15 16 10 5 21"></polyline>
        </svg>
        <span v-if="uploadedImages.length > 0" class="badge-count">{{ uploadedImages.length }}</span>
      </label>

      <button
        class="generate-btn"
        type="button"
        @click="$emit('generate')"
        :disabled="!modelValue.trim() || loading"
      >
        <span v-if="loading" class="spinner-sm"></span>
        <span v-else>生成笔记大纲</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onUnmounted } from 'vue'

interface UploadedImage {
  file: File
  preview: string
}

defineProps<{
  modelValue: string
  loading: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'generate'): void
  (e: 'imagesChange', images: File[]): void
}>()

const textareaRef = ref<HTMLTextAreaElement | null>(null)
const uploadedImages = ref<UploadedImage[]>([])

function handleInput(event: Event) {
  const target = event.target as HTMLTextAreaElement
  emit('update:modelValue', target.value)
  adjustHeight()
}

function handleEnter(e: KeyboardEvent) {
  if (e.shiftKey) return
  emit('generate')
}

function adjustHeight() {
  const el = textareaRef.value
  if (!el) return

  el.style.height = 'auto'
  const newHeight = Math.max(58, Math.min(el.scrollHeight, 180))
  el.style.height = newHeight + 'px'
}

function handleImageUpload(event: Event) {
  const target = event.target as HTMLInputElement
  if (!target.files) return

  Array.from(target.files).forEach((file) => {
    if (uploadedImages.value.length >= 5) return
    uploadedImages.value.push({ file, preview: URL.createObjectURL(file) })
  })

  emitImagesChange()
  target.value = ''
}

function removeImage(index: number) {
  const img = uploadedImages.value[index]
  URL.revokeObjectURL(img.preview)
  uploadedImages.value.splice(index, 1)
  emitImagesChange()
}

function emitImagesChange() {
  emit('imagesChange', uploadedImages.value.map(img => img.file))
}

function clearPreviews() {
  uploadedImages.value.forEach(img => URL.revokeObjectURL(img.preview))
  uploadedImages.value = []
}

onUnmounted(() => {
  clearPreviews()
})

defineExpose({
  clearPreviews
})
</script>

<style scoped>
.composer-container {
  max-width: 720px;
  padding: 14px;
  border: 1px solid #f0d9dd;
  border-radius: 24px;
  background: #fff;
  box-shadow: 0 18px 50px rgba(255, 36, 66, 0.12);
}

.composer-input-wrapper {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 8px 10px 4px;
}

.search-icon-static {
  flex-shrink: 0;
  padding-top: 10px;
  color: #ff2442;
}

.composer-textarea {
  flex: 1;
  min-height: 58px;
  max-height: 180px;
  padding: 8px 0;
  border: none;
  outline: none;
  resize: none;
  background: transparent;
  color: #1f1f1f;
  caret-color: #ff2442;
  -webkit-text-fill-color: #1f1f1f;
  font-family: inherit;
  font-size: 17px;
  line-height: 1.6;
}

.composer-textarea::placeholder {
  color: #9b8b8f;
  opacity: 1;
}

.composer-textarea::selection {
  background: rgba(255, 36, 66, 0.18);
  color: #111;
  -webkit-text-fill-color: #111;
}

.uploaded-images-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin: 12px 0 0;
  padding: 12px;
  border-radius: 18px;
  background: #fff6f7;
}

.uploaded-image-item {
  position: relative;
  width: 62px;
  height: 62px;
  overflow: hidden;
  border-radius: 14px;
  box-shadow: 0 8px 20px rgba(33, 20, 20, 0.1);
}

.uploaded-image-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.remove-image-btn {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 22px;
  height: 22px;
  display: grid;
  place-items: center;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.62);
  color: #fff;
  cursor: pointer;
}

.upload-hint {
  margin-left: auto;
  color: #9a7379;
  font-size: 13px;
}

.composer-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  margin-top: 10px;
  padding-top: 12px;
  border-top: 1px solid #f5e8ea;
}

.tool-btn {
  position: relative;
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  border: none;
  border-radius: 50%;
  background: #fff3f5;
  color: #ff2442;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tool-btn:hover,
.tool-btn.active {
  background: #ff2442;
  color: #fff;
}

.badge-count {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 18px;
  height: 18px;
  display: grid;
  place-items: center;
  padding: 0 4px;
  border-radius: 999px;
  background: #111;
  color: #fff;
  font-size: 11px;
  font-weight: 800;
}

.generate-btn {
  min-width: 150px;
  height: 46px;
  padding: 0 24px;
  border: none;
  border-radius: 999px;
  background: #ff2442;
  color: #fff;
  font-size: 15px;
  font-weight: 800;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 12px 26px rgba(255, 36, 66, 0.24);
}

.generate-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  background: #ff3d58;
}

.generate-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  box-shadow: none;
}

.spinner-sm {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
