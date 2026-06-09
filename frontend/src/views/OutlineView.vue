<template>
  <div class="container" style="max-width: 100%;">
    <div class="page-header" style="max-width: 1200px; margin: 0 auto 30px auto;">
      <div>
        <h1 class="page-title">编辑大纲</h1>
        <p class="page-subtitle">
          调整页面顺序，修改文案，打造完美内容
          <span class="save-indicator" :class="saveStatus">{{ saveStatusText }}</span>
          <span v-if="saveError" class="save-error">{{ saveError }}</span>
        </p>
      </div>
      <div class="header-actions">
        <button class="btn btn-secondary" @click="goBack" style="background: white; border: 1px solid var(--border-color);">
          上一步
        </button>
        <button class="btn btn-primary" @click="startGeneration('single')">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 6px;"><path d="M20.24 12.24a6 6 0 0 0-8.49-8.49L5 10.5V19h8.5z"></path><line x1="16" y1="8" x2="2" y2="22"></line><line x1="17.5" y1="15" x2="9" y2="15"></line></svg>
          生成 1 张封面预览
        </button>
        <button
          class="btn selected-generate-btn"
          @click="startSelectedGeneration"
          :disabled="selectedPageIndexes.length === 0"
        >
          生成已选 {{ selectedPageIndexes.length }} 张
        </button>
        <button class="btn full-generate-btn" @click="startGeneration('all')">
          生成整套 {{ store.outline.pages.length }} 张
        </button>
      </div>
    </div>

    <div class="generation-tip">
      <div>
        <strong>建议先生成 1 张预览</strong>
        <span>{{ generationModeHint }}</span>
      </div>
      <div class="generation-mode-toggle" role="group" aria-label="图片生成模式">
        <button
          type="button"
          :class="{ active: generationQuality === 'fast' }"
          @click="generationQuality = 'fast'"
        >
          快速
        </button>
        <button
          type="button"
          :class="{ active: generationQuality === 'fine' }"
          @click="generationQuality = 'fine'"
        >
          精细
        </button>
      </div>
    </div>

    <div class="selection-toolbar">
      <div>
        <strong>多选生成</strong>
        <span>勾选要生成图片的页面，只会消耗已选页面的图片额度。</span>
      </div>
      <div class="selection-actions">
        <button type="button" @click="selectAllPages">全选</button>
        <button type="button" @click="clearSelectedPages" :disabled="selectedPageIndexes.length === 0">清空</button>
      </div>
    </div>

    <div class="outline-grid">
      <div 
        v-for="(page, idx) in store.outline.pages" 
        :key="page.index"
        class="card outline-card"
        :draggable="true"
        @dragstart="onDragStart($event, idx)"
        @dragover.prevent="onDragOver($event, idx)"
        @drop="onDrop($event, idx)"
        :class="{ 'dragging-over': dragOverIndex === idx, selected: isPageSelected(page.index) }"
      >
        <!-- 拖拽手柄 (改为右上角或更加隐蔽) -->
        <div class="card-top-bar">
          <div class="page-info">
             <label class="page-select" title="选择这一页用于批量生成">
               <input
                 type="checkbox"
                 :checked="isPageSelected(page.index)"
                 @change="togglePageSelection(page.index)"
               />
               <span></span>
             </label>
             <span class="page-number">P{{ idx + 1 }}</span>
             <span class="page-type" :class="page.type">{{ getPageTypeName(page.type) }}</span>
          </div>
          
          <div class="card-controls">
            <button class="page-generate-btn" @click="startGeneration('page', page.index)" title="只生成这一页图片">
              生成此页
            </button>
            <div class="drag-handle" title="拖拽排序">
               <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#999" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="12" r="1"></circle><circle cx="9" cy="5" r="1"></circle><circle cx="9" cy="19" r="1"></circle><circle cx="15" cy="12" r="1"></circle><circle cx="15" cy="5" r="1"></circle><circle cx="15" cy="19" r="1"></circle></svg>
            </div>
            <button class="icon-btn" @click="deletePage(idx)" title="删除此页">
               <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
            </button>
          </div>
        </div>

        <div class="page-image-preview" :class="{ empty: !getPageImage(page.index)?.url }">
          <img
            v-if="getPageImage(page.index)?.url"
            :src="getPageImage(page.index)?.url"
            :alt="`第 ${idx + 1} 页图片`"
          />
          <div v-else class="image-empty-state">
            <span>未生成图片</span>
            <button type="button" @click.stop="startGeneration('page', page.index)">生成此页</button>
          </div>
        </div>

        <textarea
          v-model="page.content"
          class="textarea-paper"
          placeholder="在此输入文案..."
          @input="store.updatePage(page.index, page.content)"
        />
        
        <div class="word-count">{{ page.content.length }} 字</div>
      </div>

      <!-- 添加按钮卡片 -->
      <div class="card add-card-dashed" @click="addPage('content')">
        <div class="add-content">
          <div class="add-icon">+</div>
          <span>添加页面</span>
        </div>
      </div>
    </div>
    
    <div style="height: 100px;"></div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useGeneratorStore } from '../stores/generator'
import { useDraftAutosave } from '../composables/useDraftAutosave'

const router = useRouter()
const store = useGeneratorStore()

const dragOverIndex = ref<number | null>(null)
const draggedIndex = ref<number | null>(null)
const selectedPageIndexes = ref<number[]>([])
const generationQuality = ref<'fast' | 'fine'>('fast')
const { saveStatus, saveStatusText, saveError, flushPendingSave } = useDraftAutosave({
  debounceMs: 800,
  immediate: true
})

const getPageTypeName = (type: string) => {
  const names = {
    cover: '封面',
    content: '内容',
    summary: '总结'
  }
  return names[type as keyof typeof names] || '内容'
}

// 拖拽逻辑
const onDragStart = (e: DragEvent, index: number) => {
  draggedIndex.value = index
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.dropEffect = 'move'
  }
}

const onDragOver = (e: DragEvent, index: number) => {
  if (draggedIndex.value === index) return
  dragOverIndex.value = index
}

const onDrop = (e: DragEvent, index: number) => {
  dragOverIndex.value = null
  if (draggedIndex.value !== null && draggedIndex.value !== index) {
    store.movePage(draggedIndex.value, index)
  }
  draggedIndex.value = null
}

const deletePage = (index: number) => {
  if (confirm('确定要删除这一页吗？')) {
    store.deletePage(index)
  }
}

const addPage = (type: 'cover' | 'content' | 'summary') => {
  store.addPage(type, '')
  // 滚动到底部
  nextTick(() => {
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
  })
}

const goBack = () => {
  router.back()
}

const isPageSelected = (pageIndex: number) => selectedPageIndexes.value.includes(pageIndex)

const togglePageSelection = (pageIndex: number) => {
  if (isPageSelected(pageIndex)) {
    selectedPageIndexes.value = selectedPageIndexes.value.filter(index => index !== pageIndex)
    return
  }
  selectedPageIndexes.value = [...selectedPageIndexes.value, pageIndex]
}

const selectAllPages = () => {
  selectedPageIndexes.value = store.outline.pages.map(page => page.index)
}

const clearSelectedPages = () => {
  selectedPageIndexes.value = []
}

const generationModeHint = computed(() => {
  if (generationQuality.value === 'fast') {
    return '快速模式会直接并发生成，不等待封面参考图，速度更快但风格统一性略弱。'
  }
  return '精细模式会先生成封面，再用封面作为参考图统一整套风格。'
})

const getPageImage = (pageIndex: number) => {
  return store.images.find(image => image.index === pageIndex && image.status === 'done' && image.url)
}

const startGeneration = async (mode: 'single' | 'all' | 'page' | 'selected' = 'all', pageIndex?: number, pageIndexes?: number[]) => {
  const saved = await flushPendingSave()
  if (!saved) {
    const confirmed = confirm('草稿保存失败，仍然继续生成图片吗？')
    if (!confirmed) return
  }

  const query: Record<string, string> = { mode, quality: generationQuality.value }
  if (pageIndex !== undefined) {
    query.page = String(pageIndex)
  }
  if (pageIndexes && pageIndexes.length > 0) {
    query.pages = pageIndexes.join(',')
  }
  router.push({
    path: '/generate',
    query
  })
}

const startSelectedGeneration = () => {
  if (selectedPageIndexes.value.length === 0) return
  const orderedIndexes = store.outline.pages
    .map(page => page.index)
    .filter(index => selectedPageIndexes.value.includes(index))
  startGeneration('selected', undefined, orderedIndexes)
}


</script>

<style scoped>
/* 保存状态指示器 */
.save-indicator {
  margin-left: 12px;
  font-size: 12px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 4px;
  transition: all 0.3s ease;
}

.save-indicator.saving {
  color: #1890ff;
  background: #e6f7ff;
  border: 1px solid #91d5ff;
}

.save-indicator.saved {
  color: #52c41a;
  background: #f6ffed;
  border: 1px solid #b7eb8f;
  opacity: 0.7;
}

.save-indicator.error {
  color: #ff4d4f;
  background: #fff1f0;
  border: 1px solid #ffa39e;
}

.save-indicator.idle {
  color: #8a6e73;
  background: #fff8f9;
  border: 1px solid #f0d9dd;
}

.save-error {
  margin-left: 8px;
  color: #ff4d4f;
  font-size: 12px;
}

.header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: flex-end;
}

.full-generate-btn {
  border: 1px solid #f0d9dd;
  background: #fff;
  color: #7b666b;
}

.selected-generate-btn {
  border: 1px solid rgba(255, 36, 66, 0.22);
  background: #fff0f2;
  color: var(--primary);
  font-weight: 700;
}

.selected-generate-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.full-generate-btn:hover,
.selected-generate-btn:hover:not(:disabled) {
  border-color: var(--primary);
  color: var(--primary);
}

.generation-tip {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: center;
  max-width: 1200px;
  margin: -14px auto 24px;
  padding: 14px 18px;
  border: 1px solid #f3dfe3;
  border-radius: 16px;
  background: #fff8f9;
}

.generation-tip strong,
.generation-tip span {
  display: block;
}

.generation-tip strong {
  color: #241d1f;
  font-size: 15px;
  margin-bottom: 4px;
}

.generation-tip span,
.generation-tip em {
  color: #8a6e73;
  font-size: 13px;
  line-height: 1.5;
}

.generation-tip em {
  flex: 0 0 auto;
  font-style: normal;
  font-weight: 700;
}

.generation-mode-toggle {
  display: flex;
  flex: 0 0 auto;
  padding: 3px;
  border: 1px solid #f0d9dd;
  border-radius: 999px;
  background: #fff;
}

.generation-mode-toggle button {
  min-height: 30px;
  padding: 0 14px;
  border: none;
  border-radius: 999px;
  background: transparent;
  color: #8a6e73;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}

.generation-mode-toggle button.active {
  background: var(--primary);
  color: #fff;
  box-shadow: 0 8px 18px rgba(255, 36, 66, 0.18);
}

.selection-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: center;
  max-width: 1200px;
  margin: 0 auto 20px;
  padding: 14px 18px;
  border: 1px solid #f1eeee;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 8px 26px rgba(33, 20, 20, 0.04);
}

.selection-toolbar strong,
.selection-toolbar span {
  display: block;
}

.selection-toolbar strong {
  color: #241d1f;
  font-size: 15px;
  margin-bottom: 4px;
}

.selection-toolbar span {
  color: #8a6e73;
  font-size: 13px;
}

.selection-actions {
  display: flex;
  gap: 10px;
}

.selection-actions button {
  min-height: 32px;
  padding: 0 12px;
  border: 1px solid #f0d9dd;
  border-radius: 999px;
  background: #fff;
  color: #7b666b;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.selection-actions button:hover:not(:disabled) {
  border-color: var(--primary);
  color: var(--primary);
}

.selection-actions button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

@media (max-width: 760px) {
  .generation-tip,
  .selection-toolbar {
    display: grid;
    margin-left: 20px;
    margin-right: 20px;
  }

  .generation-tip em,
  .generation-mode-toggle {
    flex: auto;
  }
}

/* 网格布局 */
.outline-grid {
  display: grid;
  /* 响应式列：最小宽度 280px，自动填充 */
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 24px;
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 20px;
}

.outline-card {
  display: flex;
  flex-direction: column;
  padding: 16px; /* 减小内边距 */
  transition: all 0.2s ease;
  border: none;
  border-radius: 8px; /* 较小的圆角 */
  background: white;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  min-height: 620px;
  position: relative;
}

.outline-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.08);
  z-index: 10;
}

.outline-card.dragging-over {
  border: 2px dashed var(--primary);
  opacity: 0.8;
}

.outline-card.selected {
  box-shadow: 0 0 0 2px rgba(255, 36, 66, 0.22), 0 10px 28px rgba(255, 36, 66, 0.1);
}

/* 顶部栏 */
.card-top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f5f5f5;
}

.page-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-select {
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  cursor: pointer;
}

.page-select input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.page-select span {
  width: 18px;
  height: 18px;
  border: 1px solid #e6cfd4;
  border-radius: 6px;
  background: #fff;
  transition: all 0.18s ease;
}

.page-select input:checked + span {
  border-color: var(--primary);
  background: var(--primary);
  box-shadow: inset 0 0 0 4px #fff;
}

.page-number {
  font-size: 14px;
  font-weight: 700;
  color: #ccc;
  font-family: 'Inter', sans-serif;
}

.page-type {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.page-type.cover { color: #FF4D4F; background: #FFF1F0; }
.page-type.content { color: #8c8c8c; background: #f5f5f5; }
.page-type.summary { color: #52C41A; background: #F6FFED; }

.card-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  opacity: 0.4;
  transition: opacity 0.2s;
}
.outline-card:hover .card-controls { opacity: 1; }

.page-generate-btn {
  min-height: 26px;
  padding: 0 9px;
  border: 1px solid #f0d9dd;
  border-radius: 999px;
  background: #fff8f9;
  color: var(--primary);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
}

.page-generate-btn:hover {
  border-color: var(--primary);
  background: var(--primary);
  color: #fff;
}

.drag-handle {
  cursor: grab;
  padding: 2px;
}
.drag-handle:active { cursor: grabbing; }

.icon-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: #999;
  padding: 2px;
  transition: color 0.2s;
}
.icon-btn:hover { color: #FF4D4F; }

.page-image-preview {
  position: relative;
  width: 100%;
  aspect-ratio: 4 / 3;
  max-height: 320px;
  overflow: hidden;
  margin-bottom: 14px;
  border: 1px solid #f1eeee;
  border-radius: 10px;
  background: #fafafa;
}

.page-image-preview img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}

.page-image-preview.empty {
  aspect-ratio: 3 / 2;
  max-height: 230px;
  display: grid;
  place-items: center;
  background: #fff8f9;
}

.image-empty-state {
  display: grid;
  gap: 10px;
  justify-items: center;
  color: #a28b90;
  font-size: 13px;
  font-weight: 700;
}

.image-empty-state button {
  min-height: 32px;
  padding: 0 12px;
  border: 1px solid rgba(255, 36, 66, 0.22);
  border-radius: 999px;
  background: #fff;
  color: var(--primary);
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}

.image-empty-state button:hover {
  border-color: var(--primary);
  background: var(--primary);
  color: #fff;
}

/* 文本区域 - 核心 */
.textarea-paper {
  flex: 1;
  width: 100%;
  min-height: 180px;
  border: none;
  background: transparent;
  padding: 2px 0;
  font-size: 16px;
  line-height: 1.75;
  color: #333;
  resize: vertical;
  font-family: inherit;
  margin-bottom: 10px;
}

.textarea-paper:focus {
  outline: none;
}

.word-count {
  text-align: right;
  font-size: 11px;
  color: #ddd;
  margin-top: auto;
}

/* 添加卡片 */
.add-card-dashed {
  border: 2px dashed #eee;
  background: transparent;
  box-shadow: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  min-height: 620px;
  color: #ccc;
  transition: all 0.2s;
}

.add-card-dashed:hover {
  border-color: var(--primary);
  color: var(--primary);
  background: rgba(255, 36, 66, 0.02);
}

.add-content {
  text-align: center;
}

.add-icon {
  font-size: 32px;
  font-weight: 300;
  margin-bottom: 8px;
}
</style>
