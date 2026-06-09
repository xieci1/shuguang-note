<template>
  <div v-if="visible" class="publish-modal-backdrop" @click.self="close">
    <div class="publish-modal">
      <div class="publish-modal-header">
        <div>
          <span>小红书发布草稿</span>
          <h2>选择账号并发布</h2>
        </div>
        <button type="button" class="modal-close" @click="close">x</button>
      </div>

      <div v-if="publishError" class="publish-error">{{ publishError }}</div>

      <div class="publish-section">
        <label>发布账号</label>
        <div class="account-row">
          <select v-model="selectedAccountId">
            <option value="">选择一个账号</option>
            <option v-for="account in publishAccounts" :key="account.id" :value="account.id">
              {{ account.name }} · {{ account.status }}
            </option>
          </select>
          <button type="button" class="btn" @click="openSelectedAccountLogin" :disabled="!selectedAccountId || publishLoading">
            打开登录
          </button>
        </div>
        <div class="account-create-row">
          <input v-model="newAccountName" placeholder="新账号名称，例如：主账号" />
          <button type="button" class="btn" @click="addPublishAccount" :disabled="!newAccountName.trim() || publishLoading">
            添加账号
          </button>
        </div>
      </div>

      <div class="publish-section">
        <label>选择标题</label>
        <select v-model="selectedTitle">
          <option value="">选择一个标题</option>
          <option v-for="title in titleOptions" :key="title" :value="title">
            {{ title }}
          </option>
        </select>
      </div>

      <div class="publish-section">
        <label>选择正文</label>
        <select v-model="selectedBodySource" @change="applySelectedBody">
          <option v-for="option in bodyOptions" :key="option.key" :value="option.key">
            {{ option.label }}
          </option>
        </select>
      </div>

      <div class="publish-section">
        <div class="label-row">
          <label>选择发布图片</label>
          <div class="image-select-actions">
            <button type="button" class="mini-btn" @click="selectAllImages">全选</button>
            <button type="button" class="mini-btn" @click="clearSelectedImages">清空</button>
          </div>
        </div>
        <div class="publish-image-grid">
          <button
            v-for="item in publishableImageItems"
            :key="item.pageIndex"
            type="button"
            class="publish-image-item"
            :class="{ selected: selectedPageIndexes.includes(item.pageIndex) }"
            @click="toggleSelectedImage(item.pageIndex)"
          >
            <img :src="item.url" :alt="`P${item.position + 1}`" />
            <span>P{{ item.position + 1 }}</span>
          </button>
        </div>
        <div class="publish-media-summary">
          已选择 {{ selectedPageIndexes.length }} / {{ publishableImageItems.length }} 张图片发布。
        </div>
      </div>

      <div class="publish-section">
        <label>正文预览</label>
        <textarea v-model="publishBody" rows="6" />
      </div>

      <div class="publish-section">
        <div class="label-row">
          <label>标签</label>
          <button type="button" class="mini-btn" @click="generateTags" :disabled="tagLoading || !selectedTitle || !publishBody.trim()">
            {{ tagLoading ? '生成中...' : 'AI 生成标签' }}
          </button>
        </div>
        <div v-if="editableTags.length > 0" class="publish-tags">
          <button v-for="tag in editableTags" :key="tag" type="button" @click="removeTag(tag)">
            #{{ tag }} <span>x</span>
          </button>
        </div>
        <div class="tag-edit-row">
          <input v-model="tagInput" placeholder="输入标签，回车添加" @keydown.enter.prevent="addTagFromInput" />
          <button type="button" class="btn" @click="addTagFromInput" :disabled="!tagInput.trim()">添加</button>
        </div>
        <div v-if="editableTags.length === 0" class="publish-media-summary">还没有标签，可以 AI 生成或手动添加。</div>
      </div>

      <div v-if="publishJob" class="publish-job">
        <strong>{{ publishJobStatusText }}</strong>
        <p v-if="publishJob.error">{{ publishJob.error }}</p>
        <pre v-if="publishJob.logs">{{ publishJob.logs }}</pre>
      </div>

      <div class="publish-actions">
        <button type="button" class="btn" @click="close">取消</button>
        <button type="button" class="btn btn-primary" @click="createAndRunPublish" :disabled="!canRunPublish || publishLoading">
          {{ publishLoading ? '发布中...' : '立即发布到小红书' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import {
  createPublishAccount,
  createPublishDraft,
  getPublishAccounts,
  getPublishJob,
  openPublishLogin,
  runPublishDraft,
  suggestPublishTags,
  getImageUrl,
  type PublishAccount,
  type PublishJob
} from '../../api'

const props = defineProps<{
  visible: boolean
  recordId: string
  titles: string[]
  body: string
  fallbackTitle?: string
  fallbackBody?: string
  pages?: Array<{
    index: number
    type: string
    content: string
  }>
  tags: string[]
  imageCount: number
  images?: {
    task_id: string | null
    generated: string[]
  }
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const publishAccounts = ref<PublishAccount[]>([])
const selectedAccountId = ref('')
const newAccountName = ref('')
const selectedTitle = ref('')
const selectedBodySource = ref('')
const publishBody = ref('')
const publishError = ref('')
const publishLoading = ref(false)
const tagLoading = ref(false)
const tagInput = ref('')
const editableTags = ref<string[]>([])
const publishJob = ref<PublishJob | null>(null)
const selectedPageIndexes = ref<number[]>([])
let publishPollTimer: number | null = null

const publishableImageItems = computed(() => {
  const taskId = props.images?.task_id
  const generated = props.images?.generated || []
  if (!taskId) return []
  return generated
    .map((filename, index) => ({
      filename,
      pageIndex: index,
      position: Math.max(props.pages?.findIndex(page => page.index === index) ?? index, 0),
      url: filename ? getImageUrl(taskId, filename) : ''
    }))
    .filter(item => item.filename && item.url)
})

const titleOptions = computed(() => {
  const values = [...extractOutlineTitles(), ...(props.titles || [])]
  if (props.fallbackTitle) values.push(props.fallbackTitle)
  return Array.from(new Set(
    values
      .map(title => String(title).trim())
      .filter(title => title && isGoodPublishTitle(title))
  ))
})

const bodyOptions = computed(() => {
  const options: Array<{ key: string; label: string; value: string }> = []
  if (props.body?.trim()) {
    options.push({ key: 'generated', label: '内容生成区文案', value: props.body.trim() })
  }
  const pages = props.pages || []
  const selected = new Set(selectedPageIndexes.value)
  const selectedPageBodies = pages
    .filter(page => selected.has(page.index))
    .map((page, position) => ({
      key: `page-${page.index}`,
      label: `P${position + 1} ${page.type === 'cover' ? '封面' : '内容'}`,
      value: cleanPageContent(page.content)
    }))
    .filter(option => option.value)
  const allPageBodies = pages
    .map((page, position) => ({
      key: `all-page-${page.index}`,
      label: `P${position + 1} ${page.type === 'cover' ? '封面' : '内容'}`,
      value: cleanPageContent(page.content)
    }))
    .filter(option => option.value)
  if (selectedPageBodies.length > 0) {
    options.push({
      key: 'outline-selected',
      label: '已选页面内容',
      value: selectedPageBodies.map(option => option.value).join('\n\n')
    })
  }
  if (allPageBodies.length > 0) {
    options.push({
      key: 'outline-all',
      label: '全部编辑内容',
      value: allPageBodies.map(option => option.value).join('\n\n')
    })
    options.push(...allPageBodies)
  }
  if (props.fallbackBody?.trim() && !options.some(option => option.value === props.fallbackBody?.trim())) {
    options.push({ key: 'fallback', label: '编辑内容', value: props.fallbackBody.trim() })
  }
  return options
})

const canRunPublish = computed(() => {
  return !!props.recordId
    && !!selectedAccountId.value
    && !!selectedTitle.value
    && !!publishBody.value.trim()
    && selectedPageIndexes.value.length > 0
})

const publishJobStatusText = computed(() => {
  const status = publishJob.value?.status
  if (status === 'queued') return '发布任务排队中'
  if (status === 'running') return '正在发布到小红书'
  if (status === 'ready_for_review') return '发布完成'
  if (status === 'failed') return '发布任务失败'
  if (status === 'cancelled') return '发布任务已取消'
  return '发布任务状态'
})

watch(
  () => props.visible,
  async (visible) => {
    if (!visible) return
    publishError.value = ''
    publishJob.value = null
    selectedTitle.value = titleOptions.value[0] || ''
    selectedPageIndexes.value = publishableImageItems.value.map(item => item.pageIndex)
    selectedBodySource.value = bodyOptions.value[0]?.key || ''
    publishBody.value = bodyOptions.value[0]?.value || ''
    editableTags.value = normalizeTags(props.tags || [])
    tagInput.value = ''
    if (!selectedTitle.value || !publishBody.value.trim()) {
      publishError.value = '这条作品还没有可发布的标题或正文，请先编辑内容。'
    }
    if (publishableImageItems.value.length === 0) {
      publishError.value = '这条作品还没有已生成图片，暂时不能发布。'
    }
    await loadPublishAccounts()
  },
  { immediate: true }
)

watch(selectedPageIndexes, () => {
  if (selectedBodySource.value === 'outline-selected' || selectedBodySource.value.startsWith('page-')) {
    selectedBodySource.value = bodyOptions.value[0]?.key || ''
    publishBody.value = bodyOptions.value[0]?.value || ''
  }
})

function close() {
  stopPublishPolling()
  emit('close')
}

function normalizeTags(tags: string[]) {
  const values = tags
    .map(tag => String(tag).trim().replace(/^#+/, ''))
    .map(tag => tag.replace(/\s+/g, ''))
    .filter(Boolean)
  return Array.from(new Set(values)).slice(0, 10)
}

function addTagFromInput() {
  const next = normalizeTags([...editableTags.value, tagInput.value])
  editableTags.value = next
  tagInput.value = ''
}

function removeTag(tag: string) {
  editableTags.value = editableTags.value.filter(item => item !== tag)
}

async function generateTags() {
  if (!selectedTitle.value || !publishBody.value.trim()) return
  tagLoading.value = true
  publishError.value = ''
  try {
    const result = await suggestPublishTags({
      title: selectedTitle.value,
      body: publishBody.value
    })
    if (!result.success || !result.tags) {
      publishError.value = result.error || '生成标签失败'
      return
    }
    editableTags.value = normalizeTags(result.tags)
  } catch (e: any) {
    publishError.value = e.response?.data?.error || e.message || '生成标签失败'
  } finally {
    tagLoading.value = false
  }
}

function applySelectedBody() {
  const option = bodyOptions.value.find(item => item.key === selectedBodySource.value)
  publishBody.value = option?.value || ''
}

function toggleSelectedImage(pageIndex: number) {
  if (selectedPageIndexes.value.includes(pageIndex)) {
    selectedPageIndexes.value = selectedPageIndexes.value.filter(index => index !== pageIndex)
    return
  }
  selectedPageIndexes.value = [...selectedPageIndexes.value, pageIndex].sort((a, b) => a - b)
}

function selectAllImages() {
  selectedPageIndexes.value = publishableImageItems.value.map(item => item.pageIndex)
}

function clearSelectedImages() {
  selectedPageIndexes.value = []
}

function extractOutlineTitles() {
  const values: string[] = []
  const pages = props.pages || []
  const orderedPages = [
    ...pages.filter(page => page.type === 'cover'),
    ...pages.filter(page => page.type !== 'cover')
  ]
  for (const page of orderedPages) {
    for (const line of String(page.content || '').split(/\r?\n/)) {
      const match = line.match(/^\s*(?:标题|主标题)\s*[:：]\s*(.+?)\s*$/)
      if (match?.[1] && !isPublishInstructionLine(match[1])) values.push(match[1])
    }
  }
  return values
}

function cleanPageContent(content: string) {
  return String(content || '')
    .split(/\r?\n/)
    .map(line => line.trim())
    .filter(line => line && !shouldDropPublishLine(line))
    .join('\n')
}

function shouldDropPublishLine(line: string) {
  return /^\[(封面|内容|总结)\]$/.test(line)
    || isPublishInstructionLine(line)
}

function isPublishInstructionLine(line: string) {
  const text = String(line || '').trim()
  return /^(画面建议|配图建议|图片建议|视觉建议|封面建议|设计建议|插画建议|生成建议|提示词)\s*[:：]/.test(text)
    || /^我想(推广|宣传|介绍|发布|做|生成)/.test(text)
    || /^帮我(写|生成|做|出|制作)/.test(text)
    || /^请(围绕|根据|帮|生成|写|做|输出|制作)/.test(text)
    || /生成一套.*(小红书|图文|大纲|文案)/.test(text)
    || /(内容需包括|需要包括|需包含|输出包括|生成结果包括)/.test(text)
    || /(小红书多页图文大纲|多页图文大纲)/.test(text)
    || /生成结果包括/.test(text)
}

function isGoodPublishTitle(title: string) {
  const text = String(title || '').trim()
  if (!text || isPublishInstructionLine(text)) return false
  if (text.length > 38) return false
  return true
}

async function loadPublishAccounts() {
  try {
    const result = await getPublishAccounts('xhs')
    if (result.success) {
      publishAccounts.value = result.accounts
      if (!selectedAccountId.value && result.accounts.length > 0) {
        selectedAccountId.value = result.accounts[0].id
      }
    }
  } catch (e: any) {
    publishError.value = e.message || '加载发布账号失败'
  }
}

async function addPublishAccount() {
  publishLoading.value = true
  publishError.value = ''
  try {
    const result = await createPublishAccount(newAccountName.value.trim(), 'xhs')
    if (!result.success || !result.account_id) {
      publishError.value = result.error || '添加账号失败'
      return
    }
    newAccountName.value = ''
    selectedAccountId.value = result.account_id
    await loadPublishAccounts()
  } catch (e: any) {
    publishError.value = e.response?.data?.error || e.message || '添加账号失败'
  } finally {
    publishLoading.value = false
  }
}

async function openSelectedAccountLogin() {
  if (!selectedAccountId.value) return
  publishLoading.value = true
  publishError.value = ''
  try {
    const result = await openPublishLogin(selectedAccountId.value)
    if (!result.success) {
      publishError.value = result.error || '打开登录失败'
    } else {
      await loadPublishAccounts()
    }
  } catch (e: any) {
    publishError.value = e.response?.data?.error || e.message || '打开登录失败'
  } finally {
    publishLoading.value = false
  }
}

async function createAndRunPublish() {
  if (!canRunPublish.value) return
  publishLoading.value = true
  publishError.value = ''
  publishJob.value = null
  try {
    const draft = await createPublishDraft({
      creation_id: props.recordId,
      account_id: selectedAccountId.value,
      title: selectedTitle.value,
      body: publishBody.value,
      tags: editableTags.value,
      page_indexes: selectedPageIndexes.value
    })
    if (!draft.success || !draft.draft_id) {
      publishError.value = draft.error || '创建发布草稿失败'
      return
    }
    const run = await runPublishDraft(draft.draft_id)
    if (!run.success || !run.job_id) {
      publishError.value = run.error || '启动发布任务失败'
      return
    }
    startPublishPolling(run.job_id)
  } catch (e: any) {
    publishError.value = e.response?.data?.error || e.message || '发布任务失败'
  } finally {
    publishLoading.value = false
  }
}

function startPublishPolling(jobId: string) {
  stopPublishPolling()
  const poll = async () => {
    try {
      const result = await getPublishJob(jobId)
      if (result.success && result.job) {
        publishJob.value = result.job
        if (!['queued', 'running'].includes(result.job.status)) {
          stopPublishPolling()
        }
      }
    } catch (e: any) {
      publishError.value = e.response?.data?.error || e.message || '查询发布任务失败'
      stopPublishPolling()
    }
  }
  poll()
  publishPollTimer = window.setInterval(poll, 1200)
}

function stopPublishPolling() {
  if (publishPollTimer !== null) {
    clearInterval(publishPollTimer)
    publishPollTimer = null
  }
}

onUnmounted(() => {
  stopPublishPolling()
})
</script>

<style scoped>
.publish-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(0, 0, 0, 0.42);
}

.publish-modal {
  width: min(760px, 100%);
  max-height: 90vh;
  overflow: auto;
  padding: 24px;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 24px 70px rgba(26, 20, 20, 0.24);
}

.publish-modal-header,
.account-row,
.account-create-row,
.publish-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
}

.publish-modal-header span {
  color: var(--primary);
  font-size: 13px;
  font-weight: 900;
}

.publish-modal-header h2 {
  margin: 4px 0 0;
  color: var(--text-main);
  font-size: 22px;
}

.modal-close {
  border: none;
  background: transparent;
  color: #999;
  font-size: 22px;
  cursor: pointer;
}

.publish-section {
  display: grid;
  gap: 8px;
  margin-top: 18px;
}

.publish-section label {
  color: #2b2022;
  font-size: 14px;
  font-weight: 800;
}

.label-row,
.tag-edit-row,
.image-select-actions {
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
}

.publish-section select,
.publish-section input,
.publish-section textarea {
  width: 100%;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  background: #fff;
  color: var(--text-main);
  font: inherit;
}

.publish-section select,
.publish-section input {
  min-height: 42px;
  padding: 0 12px;
}

.publish-section textarea {
  padding: 12px;
  resize: vertical;
  line-height: 1.7;
}

.account-row select,
.account-create-row input {
  flex: 1;
}

.publish-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.publish-tags button {
  padding: 7px 12px;
  border: none;
  border-radius: 999px;
  background: var(--primary-light);
  color: var(--primary);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.publish-tags button span {
  margin-left: 4px;
  color: #c96b78;
}

.tag-edit-row input {
  flex: 1;
}

.publish-image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(78px, 1fr));
  gap: 10px;
}

.publish-image-item {
  position: relative;
  overflow: hidden;
  padding: 0;
  border: 2px solid transparent;
  border-radius: 12px;
  background: #f7f7f7;
  cursor: pointer;
  aspect-ratio: 3/4;
}

.publish-image-item img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}

.publish-image-item span {
  position: absolute;
  left: 6px;
  top: 6px;
  padding: 3px 7px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.58);
  color: #fff;
  font-size: 11px;
  font-weight: 900;
}

.publish-image-item.selected {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(255, 36, 66, 0.12);
}

.publish-image-item.selected::after {
  content: "已选";
  position: absolute;
  right: 6px;
  bottom: 6px;
  padding: 3px 7px;
  border-radius: 999px;
  background: var(--primary);
  color: #fff;
  font-size: 11px;
  font-weight: 900;
}

.mini-btn {
  border: 1px solid rgba(255, 36, 66, 0.2);
  border-radius: 999px;
  background: #fff0f2;
  color: var(--primary);
  cursor: pointer;
  font-size: 12px;
  font-weight: 800;
  padding: 6px 12px;
}

.mini-btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.publish-media-summary {
  padding: 12px;
  border-radius: 10px;
  background: #fff8f9;
  color: #7b666b;
  font-size: 14px;
}

.publish-error {
  margin-top: 14px;
  padding: 12px;
  border-radius: 10px;
  background: #fff1f0;
  color: #d92d42;
  font-weight: 700;
}

.publish-job {
  margin-top: 18px;
  padding: 14px;
  border-radius: 12px;
  background: #f7f8fa;
}

.publish-job strong {
  color: var(--primary);
}

.publish-job pre {
  max-height: 160px;
  overflow: auto;
  white-space: pre-wrap;
  color: #555;
  font-size: 12px;
}

.publish-actions {
  margin-top: 22px;
}

@media (max-width: 640px) {
  .account-row,
  .account-create-row,
  .label-row,
  .tag-edit-row,
  .image-select-actions,
  .publish-actions {
    display: grid;
  }
}
</style>
