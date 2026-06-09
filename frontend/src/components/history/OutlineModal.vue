<template>
  <div v-if="visible && record" class="outline-modal-overlay" @click="$emit('close')">
    <div class="outline-modal-content" @click.stop>
      <div class="outline-modal-header">
        <div>
          <h3>{{ isRecoveredRecord ? '恢复任务详情' : '完整大纲' }}</h3>
          <p v-if="isRecoveredRecord">这条记录由本地图片任务恢复，原始大纲没有关联到历史记录。</p>
        </div>
        <button class="close-icon" @click="$emit('close')">×</button>
      </div>

      <div class="outline-modal-body">
        <div v-if="isRecoveredRecord" class="recovered-panel">
          <div class="recovered-summary">
            <div>
              <span>任务 ID</span>
              <strong>{{ record.images.task_id }}</strong>
            </div>
            <div>
              <span>已恢复图片</span>
              <strong>{{ generatedImages.length }} 张</strong>
            </div>
            <div>
              <span>可见页数</span>
              <strong>{{ record.outline.pages.length }} 页</strong>
            </div>
          </div>

          <div class="recovered-note">
            只能恢复已经生成的图片和页码。因为生成时没有成功写入历史记录，原始主题、大纲文案和每页说明无法自动找回。
          </div>

          <div class="recovered-grid">
            <div v-for="item in generatedImages" :key="item.filename" class="recovered-image-card">
              <img :src="getImageSrc(item.filename)" :alt="`Page ${item.pageNumber}`" />
              <span>Page {{ item.pageNumber }}</span>
            </div>
          </div>
        </div>

        <template v-else>
          <div v-for="page in record.outline.pages" :key="page.index" class="outline-page-card">
            <div class="outline-page-card-header">
              <span class="page-badge">P{{ page.index + 1 }}</span>
              <span class="page-type-badge" :class="page.type">{{ getPageTypeName(page.type) }}</span>
              <span class="word-count">{{ page.content.length }} 字</span>
            </div>
            <div class="outline-page-card-content">{{ page.content }}</div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { getImageUrl } from '../../api'

interface Page {
  index: number
  type: 'cover' | 'content' | 'summary'
  content: string
}

interface HistoryRecord {
  id: string
  title: string
  outline: {
    raw: string
    pages: Page[]
  }
  images: {
    task_id: string | null
    generated: string[]
  }
}

const props = defineProps<{
  visible: boolean
  record: HistoryRecord | null
}>()

defineEmits<{
  (e: 'close'): void
}>()

const isRecoveredRecord = computed(() => {
  if (!props.record) return false
  return props.record.title.startsWith('恢复的图片任务') ||
    props.record.outline.raw.includes('孤立图片任务自动恢复')
})

const generatedImages = computed(() => {
  if (!props.record) return []
  return props.record.images.generated
    .map((filename, index) => ({ filename, pageNumber: index + 1 }))
    .filter(item => Boolean(item.filename))
})

function getPageTypeName(type: string): string {
  const names: Record<string, string> = {
    cover: '封面',
    content: '内容',
    summary: '总结'
  }
  return names[type] || '内容'
}

function getImageSrc(filename: string) {
  return props.record?.images.task_id ? getImageUrl(props.record.images.task_id, filename) : ''
}
</script>

<style scoped>
.outline-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.outline-modal-content {
  background: white;
  width: 100%;
  max-width: 860px;
  max-height: 85vh;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.outline-modal-header {
  padding: 20px 24px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
  flex-shrink: 0;
}

.outline-modal-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #1a1a1a;
}

.outline-modal-header p {
  margin: 6px 0 0;
  color: #777;
  font-size: 13px;
}

.close-icon {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #666;
  padding: 0;
  line-height: 1;
  transition: color 0.2s;
}

.close-icon:hover {
  color: #333;
}

.outline-modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  background: #f9fafb;
}

.recovered-panel {
  display: grid;
  gap: 16px;
}

.recovered-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.recovered-summary div {
  padding: 16px;
  border: 1px solid #f1eeee;
  border-radius: 12px;
  background: #fff;
}

.recovered-summary span,
.recovered-summary strong {
  display: block;
}

.recovered-summary span {
  color: #999;
  font-size: 12px;
  margin-bottom: 8px;
}

.recovered-summary strong {
  color: #222;
  font-size: 16px;
  word-break: break-word;
}

.recovered-note {
  padding: 14px 16px;
  border: 1px solid #ffe1e6;
  border-radius: 12px;
  background: #fff8f9;
  color: #8a5f67;
  font-size: 13px;
  line-height: 1.7;
}

.recovered-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 14px;
}

.recovered-image-card {
  overflow: hidden;
  border: 1px solid #eee;
  border-radius: 12px;
  background: #fff;
}

.recovered-image-card img {
  display: block;
  width: 100%;
  aspect-ratio: 3/4;
  object-fit: cover;
}

.recovered-image-card span {
  display: block;
  padding: 10px 12px;
  color: #666;
  font-size: 12px;
  font-weight: 700;
}

.outline-page-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 16px;
  border: 1px solid #e5e7eb;
  transition: all 0.2s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.outline-page-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  border-color: #d1d5db;
}

.outline-page-card:last-child {
  margin-bottom: 0;
}

.outline-page-card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  padding-bottom: 14px;
  border-bottom: 1px solid #e5e7eb;
}

.page-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 36px;
  height: 24px;
  padding: 0 8px;
  background: var(--primary, #ff2442);
  color: white;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 700;
  font-family: 'Inter', sans-serif;
}

.page-type-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  background: #e9ecef;
  color: #6c757d;
}

.page-type-badge.cover {
  background: #e3f2fd;
  color: #1976d2;
}

.page-type-badge.content {
  background: #f3e5f5;
  color: #7b1fa2;
}

.page-type-badge.summary {
  background: #e8f5e9;
  color: #388e3c;
}

.word-count {
  margin-left: auto;
  font-size: 11px;
  color: #999;
}

.outline-page-card-content {
  font-size: 14px;
  line-height: 1.8;
  color: #374151;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
}

@media (max-width: 768px) {
  .outline-modal-overlay {
    padding: 20px;
  }

  .outline-modal-content {
    max-height: 90vh;
  }

  .outline-modal-header,
  .outline-modal-body {
    padding: 16px 20px;
  }

  .recovered-summary {
    grid-template-columns: 1fr;
  }
}
</style>
