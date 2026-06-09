<template>
  <!-- 图片画廊模态框 -->
  <div v-if="visible && record" class="modal-fullscreen" @click="$emit('close')">
    <div class="modal-body" @click.stop>
      <!-- 头部区域 -->
      <div class="modal-header">
        <div style="flex: 1;">
          <!-- 标题区域 -->
          <div class="title-section">
            <h3
              class="modal-title"
              :class="{ 'collapsed': !titleExpanded && record.title.length > 80 }"
            >
              {{ record.title }}
            </h3>
            <button
              v-if="record.title.length > 80"
              class="title-expand-btn"
              @click="titleExpanded = !titleExpanded"
            >
              {{ titleExpanded ? '收起' : '展开' }}
            </button>
          </div>

          <div class="modal-meta">
            <span>{{ generatedImagesCount }} / {{ record.outline.pages.length }} 张图片 · {{ formattedDate }}</span>
            <span v-if="showOwner && record.user">作者：{{ record.user.name }}</span>
            <button
              class="view-outline-btn"
              @click="$emit('showOutline')"
              title="查看完整大纲"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="16" y1="13" x2="8" y2="13"></line>
                <line x1="16" y1="17" x2="8" y2="17"></line>
              </svg>
              查看大纲
            </button>
          </div>
        </div>

        <div class="header-actions">
          <button class="btn edit-btn" @click="$emit('edit', record.id)">
            编辑作品
          </button>
          <button class="btn download-btn" @click="$emit('downloadAll')">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            打包下载
          </button>
          <button class="close-icon" @click="$emit('close')">×</button>
        </div>
      </div>

      <!-- 图片网格 -->
      <div class="preview-layout">
        <section class="phone-preview-panel">
          <div class="preview-switch">
            <button type="button" :class="{ active: previewMode === 'note' }" @click="previewMode = 'note'">笔记预览</button>
            <button type="button" :class="{ active: previewMode === 'cover' }" @click="previewMode = 'cover'">封面预览</button>
          </div>

          <div v-if="previewMode === 'note'" class="xhs-phone-shell note-phone">
            <div class="xhs-statusbar">
              <strong>9:41</strong>
              <span>▮▮▮ ⌕ ▰</span>
            </div>

            <div class="xhs-note-header">
              <span class="back-icon">‹</span>
              <div class="avatar">{{ authorInitial }}</div>
              <strong>{{ authorName }}</strong>
              <button type="button">关注</button>
              <span class="share-icon">⌁</span>
            </div>

            <div class="xhs-note-image">
              <img v-if="activeImageSrc" :src="activeImageSrc" :alt="`第 ${activePage.index + 1} 页图片`" />
              <div v-else class="phone-placeholder">未生成</div>
              <div v-if="regeneratingImages.has(activePage.index)" class="regenerating-mask">重绘中...</div>
            </div>

            <div class="xhs-note-content">
              <h3>{{ displayTitle }}</h3>
              <div v-if="displayTags.length" class="xhs-tags">
                <span v-for="tag in displayTags" :key="tag">#{{ normalizeTag(tag) }}</span>
              </div>
              <p>编辑于刚刚 仅自己可见</p>
            </div>

            <div class="xhs-actionbar">
              <span>⌕ 说点什么...</span>
              <strong>♡ 点赞</strong>
              <strong>☆ 收藏</strong>
              <strong>☏ 评论</strong>
            </div>
          </div>

          <div v-else class="xhs-phone-shell feed-phone">
            <div class="xhs-statusbar">
              <strong>9:41</strong>
              <span>▮▮▮ ⌕ ▰</span>
            </div>

            <div class="feed-top">
              <span>☰</span>
              <nav>
                <button>关注</button>
                <button class="active">发现</button>
                <button>附近</button>
              </nav>
              <span>⌕</span>
            </div>

            <div class="feed-tabs">
              <span>推荐</span>
              <span>直播</span>
              <span>短剧</span>
              <span>穿搭</span>
              <span>旅行</span>
            </div>

            <div class="feed-grid">
              <article class="feed-card main">
                <img v-if="coverImageSrc" :src="coverImageSrc" alt="封面预览" />
                <div v-else class="feed-placeholder"></div>
                <strong>{{ displayTitle }}</strong>
                <div class="feed-author">
                  <span class="mini-avatar">{{ authorInitial }}</span>
                  <em>{{ authorName }}</em>
                  <i>♡ 0</i>
                </div>
              </article>
              <article v-for="item in mockFeedCards" :key="item" class="feed-card">
                <div class="feed-placeholder"></div>
                <strong>{{ item }}</strong>
                <div class="feed-author">
                  <span class="mini-avatar"></span>
                  <em>用户名</em>
                  <i>♡ 0</i>
                </div>
              </article>
            </div>

            <div class="feed-bottom">
              <span>首页</span>
              <span>市集</span>
              <strong>+</strong>
              <span>消息</span>
              <span>我</span>
            </div>
          </div>

          <div class="page-strip">
            <button
              v-for="page in record.outline.pages"
              :key="page.index"
              type="button"
              class="strip-item"
              :class="{ active: page.index === activePageIndex }"
              @click="activePageIndex = page.index"
            >
              <img v-if="getImageFilename(page.index)" :src="getImageSrc(page.index)" :alt="`P${page.index + 1}`" />
              <span v-else>P{{ page.index + 1 }}</span>
            </button>
          </div>

          <div class="preview-actions">
            <button
              type="button"
              @click="$emit('regenerate', activePage.index)"
              :disabled="regeneratingImages.has(activePage.index)"
            >
              {{ regeneratingImages.has(activePage.index) ? '重绘中...' : '重新生成当前页' }}
            </button>
            <button
              type="button"
              :disabled="!getImageFilename(activePage.index)"
              @click="$emit('download', getImageFilename(activePage.index), activePage.index)"
            >
              下载当前页
            </button>
          </div>
        </section>

        <aside class="content-preview-panel">
          <div class="content-block">
            <span>发布标题</span>
            <h4>{{ displayTitle }}</h4>
          </div>

          <div class="content-block">
            <span>正文预览</span>
            <p>{{ displayBody }}</p>
          </div>

          <div v-if="displayTags.length" class="content-block">
            <span>标签</span>
            <div class="tag-list">
              <em v-for="tag in displayTags" :key="tag">#{{ normalizeTag(tag) }}</em>
            </div>
          </div>

          <div class="content-block">
            <span>当前页文案</span>
            <div class="page-copy">{{ activePage.content }}</div>
          </div>
        </aside>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { getImageUrl } from '../../api'

/**
 * 图片画廊模态框组件
 *
 * 功能：
 * - 展示历史记录的所有生成图片
 * - 支持重新生成单张图片
 * - 支持下载单张/全部图片
 * - 可展开查看完整大纲
 */

// 定义记录类型
interface ViewingRecord {
  id: string
  title: string
  updated_at: string
  outline: {
    raw: string
    pages: Array<{ index: number; type: string; content: string }>
  }
  images: {
    task_id: string
    generated: string[]
  }
  content?: {
    titles?: string[]
    copywriting?: string
    tags?: string[]
  } | null
  user?: {
    id: string
    name: string
    email: string
    role: string
  } | null
}

// 定义 Props
const props = defineProps<{
  visible: boolean
  record: ViewingRecord | null
  regeneratingImages: Set<number>
  showOwner?: boolean
}>()

// 定义 Emits
defineEmits<{
  (e: 'close'): void
  (e: 'showOutline'): void
  (e: 'edit', id: string): void
  (e: 'downloadAll'): void
  (e: 'download', filename: string, index: number): void
  (e: 'regenerate', index: number): void
}>()

// 标题展开状态
const titleExpanded = ref(false)
const activePageIndex = ref(0)
const previewMode = ref<'note' | 'cover'>('note')

const mockFeedCards = ['示例笔记标题1', '示例笔记标题2', '示例笔记标题3']

// 格式化日期
const formattedDate = computed(() => {
  if (!props.record) return ''
  const d = new Date(props.record.updated_at)
  return `${d.getMonth() + 1}/${d.getDate()}`
})

const generatedImagesCount = computed(() => {
  return props.record?.images.generated.filter(Boolean).length || 0
})

const activePage = computed(() => {
  return props.record?.outline.pages.find(page => page.index === activePageIndex.value)
    || props.record?.outline.pages[0]
    || { index: 0, type: 'content', content: '' }
})

const activeImageSrc = computed(() => {
  return getImageSrc(activePage.value.index)
})

const coverImageSrc = computed(() => {
  const first = props.record?.outline.pages.find(page => getImageFilename(page.index))
  return first ? getImageSrc(first.index) : ''
})

const authorName = computed(() => {
  return props.record?.user?.name || 'lucky'
})

const authorInitial = computed(() => {
  return authorName.value.slice(0, 1).toUpperCase()
})

const displayTitle = computed(() => {
  const outlineTitle = extractOutlineTitle()
  if (outlineTitle) return outlineTitle

  const generatedTitle = (props.record?.content?.titles || [])
    .map(cleanPreviewTitle)
    .find(isGoodPreviewTitle)
  return generatedTitle || props.record?.title || '未命名作品'
})

const displayBody = computed(() => {
  if (props.record?.content?.copywriting) return props.record.content.copywriting
  return props.record?.outline.pages
    .map((page, index) => `P${index + 1} ${page.content}`)
    .join('\n\n') || ''
})

const displayTags = computed(() => props.record?.content?.tags || [])

function getImageFilename(pageIndex: number) {
  return props.record?.images.generated[pageIndex] || ''
}

function getImageSrc(pageIndex: number) {
  const filename = getImageFilename(pageIndex)
  return props.record?.images.task_id && filename
    ? getImageUrl(props.record.images.task_id, filename)
    : ''
}

function normalizeTag(tag: string) {
  return String(tag || '').replace(/^#/, '')
}

function extractOutlineTitle() {
  const pages = props.record?.outline.pages || []
  const orderedPages = [
    ...pages.filter(page => page.type === 'cover'),
    ...pages.filter(page => page.type !== 'cover')
  ]

  for (const page of orderedPages) {
    for (const line of String(page.content || '').split(/\r?\n/)) {
      const match = line.match(/^\s*(?:标题|主标题)\s*[:：]\s*(.+?)\s*$/)
      const title = cleanPreviewTitle(match?.[1] || '')
      if (isGoodPreviewTitle(title)) return title
    }
  }
  return ''
}

function cleanPreviewTitle(title: string) {
  return String(title || '')
    .trim()
    .replace(/^["'“”‘’]+|["'“”‘’]+$/g, '')
}

function isGoodPreviewTitle(title: string) {
  const text = cleanPreviewTitle(title)
  if (!text || text.length > 38) return false
  return !isPreviewInstructionLine(text)
}

function isPreviewInstructionLine(line: string) {
  const text = String(line || '').trim()
  return /^(画面建议|配图建议|图片建议|视觉建议|封面建议|设计建议|插画建议|生成建议|提示词)\s*[:：]/.test(text)
    || /^我想(推广|宣传|介绍|发布|做|生成)/.test(text)
    || /^帮我(写|生成|做|出|制作)/.test(text)
    || /^请(围绕|根据|帮|生成|写|做|输出|制作)/.test(text)
    || /生成一套.*(小红书|图文|大纲|文案)/.test(text)
    || /(内容需包括|需要包括|需包含|输出包括|生成结果包括)/.test(text)
    || /(小红书多页图文大纲|多页图文大纲)/.test(text)
}
</script>

<style scoped>
/* 全屏模态框遮罩 */
.modal-fullscreen {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.9);
  z-index: 999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

/* 模态框主体 */
.modal-body {
  background: white;
  width: 100%;
  max-width: 1000px;
  height: 90vh;
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 头部区域 */
.modal-header {
  padding: 20px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-shrink: 0;
  gap: 20px;
}

/* 标题区域 */
.title-section {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 4px;
}

.modal-title {
  flex: 1;
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  line-height: 1.4;
  color: #1a1a1a;
  word-break: break-word;
  transition: max-height 0.3s ease;
}

.modal-title.collapsed {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

.title-expand-btn {
  flex-shrink: 0;
  padding: 2px 8px;
  background: #f0f0f0;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
  color: #666;
  transition: all 0.2s;
  margin-top: 2px;
}

.title-expand-btn:hover {
  background: var(--primary, #ff2442);
  color: white;
}

/* 元信息 */
.modal-meta {
  font-size: 12px;
  color: #999;
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
}

/* 查看大纲按钮 */
.view-outline-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  color: #495057;
  transition: all 0.2s;
}

.view-outline-btn:hover {
  background: var(--primary, #ff2442);
  color: white;
  border-color: var(--primary, #ff2442);
}

/* 头部操作区 */
.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.download-btn {
  padding: 8px 16px;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.edit-btn {
  padding: 8px 16px;
  border: 1px solid rgba(255, 36, 66, 0.22);
  background: #fff0f2;
  color: var(--primary, #ff2442);
  font-size: 14px;
  font-weight: 800;
}

.close-icon {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #666;
  padding: 0;
  line-height: 1;
}

.close-icon:hover {
  color: #333;
}

/* 成品预览布局 */
.preview-layout {
  flex: 1;
  display: grid;
  grid-template-columns: minmax(320px, 420px) minmax(0, 1fr);
  gap: 24px;
  overflow: auto;
  padding: 22px;
  background: #fafafa;
}

.phone-preview-panel,
.content-preview-panel {
  min-width: 0;
}

.phone-preview-panel {
  display: grid;
  align-content: start;
  gap: 14px;
}

.preview-switch {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
  width: 100%;
  max-width: 360px;
  justify-self: center;
  padding: 4px;
  border-radius: 999px;
  background: #ededed;
}

.preview-switch button {
  min-height: 40px;
  border: none;
  border-radius: 999px;
  background: transparent;
  color: #9a9a9a;
  font-size: 15px;
  font-weight: 800;
  cursor: pointer;
}

.preview-switch button.active {
  background: #fff;
  color: #111;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.xhs-phone-shell {
  width: 100%;
  max-width: 360px;
  justify-self: center;
  overflow: hidden;
  border: 7px solid #575757;
  border-radius: 38px;
  background: #fff;
  box-shadow: 0 24px 60px rgba(20, 18, 18, 0.16);
}

.xhs-statusbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 54px;
  padding: 0 28px;
  color: #000;
  font-size: 14px;
}

.xhs-note-header {
  display: grid;
  grid-template-columns: 28px 34px 1fr auto 28px;
  gap: 8px;
  align-items: center;
  height: 54px;
  padding: 0 14px;
}

.back-icon,
.share-icon {
  color: #333;
  font-size: 30px;
  line-height: 1;
}

.share-icon {
  font-size: 24px;
}

.avatar,
.mini-avatar {
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: #f0d7dc;
  color: #5f333b;
  font-size: 12px;
  font-weight: 900;
}

.avatar {
  width: 34px;
  height: 34px;
}

.xhs-note-header strong {
  color: #111;
  font-size: 14px;
}

.xhs-note-header button {
  min-height: 28px;
  padding: 0 14px;
  border: 1px solid #ff2442;
  border-radius: 999px;
  background: #fff;
  color: #ff2442;
  font-weight: 800;
}

.xhs-note-image {
  position: relative;
  aspect-ratio: 3/4;
  overflow: hidden;
  background: #111;
}

.xhs-note-image img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}

.phone-placeholder {
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
  color: #a0a0a0;
  font-size: 14px;
  font-weight: 700;
}

.regenerating-mask {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  background: rgba(255, 255, 255, 0.82);
  color: var(--primary, #ff2442);
  font-weight: 800;
}

.xhs-note-content {
  padding: 14px 16px 10px;
}

.xhs-note-content h3 {
  margin: 0 0 8px;
  color: #222;
  font-size: 15px;
  line-height: 1.4;
}

.xhs-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 10px;
}

.xhs-tags span {
  color: #003f8f;
  font-size: 13px;
}

.xhs-note-content p {
  margin: 0;
  color: #aaa;
  font-size: 12px;
}

.xhs-actionbar {
  display: grid;
  grid-template-columns: 1fr auto auto auto;
  gap: 10px;
  align-items: center;
  padding: 10px 14px 22px;
  color: #333;
  font-size: 12px;
}

.xhs-actionbar span {
  min-width: 0;
  padding: 8px 12px;
  border-radius: 999px;
  background: #f5f5f5;
  color: #aaa;
}

.xhs-actionbar strong {
  white-space: nowrap;
  font-size: 12px;
}

.feed-phone {
  position: relative;
}

.feed-top {
  display: grid;
  grid-template-columns: 30px 1fr 30px;
  align-items: center;
  padding: 0 18px 10px;
  color: #555;
  font-size: 20px;
}

.feed-top nav {
  display: flex;
  justify-content: center;
  gap: 24px;
}

.feed-top button {
  position: relative;
  border: none;
  background: transparent;
  color: #999;
  font-size: 16px;
  font-weight: 800;
}

.feed-top button.active {
  color: #222;
}

.feed-top button.active::after {
  content: "";
  position: absolute;
  left: 50%;
  bottom: -7px;
  width: 28px;
  height: 3px;
  border-radius: 999px;
  background: #ff2442;
  transform: translateX(-50%);
}

.feed-tabs {
  display: flex;
  gap: 18px;
  overflow: hidden;
  padding: 8px 16px 12px;
  color: #999;
  font-size: 13px;
  white-space: nowrap;
}

.feed-tabs span:first-child {
  color: #222;
  font-weight: 800;
}

.feed-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  height: 560px;
  overflow: hidden;
  padding: 0 8px 70px;
}

.feed-card {
  overflow: hidden;
  border-radius: 4px;
  background: #fff;
}

.feed-card img,
.feed-placeholder {
  width: 100%;
  aspect-ratio: 3/4;
  display: block;
  object-fit: cover;
  background: #e9e9e9;
}

.feed-card strong {
  display: -webkit-box;
  overflow: hidden;
  padding: 8px 8px 4px;
  color: #111;
  font-size: 13px;
  line-height: 1.35;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.feed-author {
  display: grid;
  grid-template-columns: 18px 1fr auto;
  gap: 5px;
  align-items: center;
  padding: 0 8px 10px;
  color: #888;
  font-size: 11px;
}

.mini-avatar {
  width: 18px;
  height: 18px;
}

.feed-author em,
.feed-author i {
  overflow: hidden;
  font-style: normal;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.feed-bottom {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  align-items: center;
  height: 58px;
  border-top: 1px solid #f1eeee;
  background: rgba(255, 255, 255, 0.96);
  color: #777;
  font-size: 13px;
  font-weight: 800;
  text-align: center;
}

.feed-bottom strong {
  display: grid;
  place-items: center;
  width: 42px;
  height: 34px;
  justify-self: center;
  border-radius: 10px;
  background: #ff2442;
  color: #fff;
  font-size: 26px;
  line-height: 1;
}

.page-strip {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  padding: 2px 4px 8px;
}

.strip-item {
  flex: 0 0 54px;
  width: 54px;
  aspect-ratio: 3/4;
  overflow: hidden;
  border: 2px solid transparent;
  border-radius: 10px;
  background: #fff;
  color: #9a8b8e;
  cursor: pointer;
  font-size: 12px;
  font-weight: 800;
}

.strip-item.active {
  border-color: var(--primary, #ff2442);
}

.strip-item img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}

.preview-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
}

.preview-actions button {
  min-height: 38px;
  padding: 0 14px;
  border: 1px solid #f2dce0;
  border-radius: 999px;
  background: #fff;
  color: var(--primary, #ff2442);
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}

.preview-actions button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.content-preview-panel {
  display: grid;
  align-content: start;
  gap: 14px;
}

.content-block {
  padding: 18px;
  border: 1px solid #f1eeee;
  border-radius: 14px;
  background: #fff;
}

.content-block span {
  display: block;
  margin-bottom: 8px;
  color: var(--primary, #ff2442);
  font-size: 12px;
  font-weight: 900;
}

.content-block h4 {
  margin: 0;
  color: #222;
  font-size: 20px;
  line-height: 1.4;
}

.content-block p,
.page-copy {
  margin: 0;
  color: #5f5357;
  font-size: 14px;
  line-height: 1.8;
  white-space: pre-wrap;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-list em {
  padding: 6px 10px;
  border-radius: 999px;
  background: #fff0f2;
  color: var(--primary, #ff2442);
  font-size: 13px;
  font-style: normal;
  font-weight: 800;
}

/* 响应式 */
@media (max-width: 768px) {
  .modal-fullscreen {
    padding: 20px;
  }

  .preview-layout {
    grid-template-columns: 1fr;
    padding: 14px;
  }

  .preview-actions {
    display: grid;
  }
}
</style>
