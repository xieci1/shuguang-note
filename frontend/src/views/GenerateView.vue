<template>
  <div class="container">
    <div class="page-header">
      <div>
        <h1 class="page-title">生成结果</h1>
        <p class="page-subtitle">
          <span v-if="isGenerating">
            {{ generationSubtitle }}
          </span>
          <span v-else-if="hasFailedImages">{{ failedCount }} 张图片生成失败，可点击重试</span>
          <span v-else>{{ generationDoneSubtitle }}</span>
        </p>
      </div>
      <div style="display: flex; gap: 10px;">
        <button
          v-if="hasFailedImages && !isGenerating"
          class="btn btn-primary"
          @click="retryAllFailed"
          :disabled="isRetrying"
        >
          {{ isRetrying ? '补全中...' : '一键补全失败图片' }}
        </button>
        <button class="btn" @click="router.push('/outline')" style="border:1px solid var(--border-color)">
          返回大纲
        </button>
      </div>
    </div>

    <div class="card">
      <div class="progress-head">
        <div>
          <span>生成进度</span>
          <strong>{{ progressPhase }}</strong>
        </div>
        <em>{{ Math.round(progressPercent) }}%</em>
      </div>
      <div class="progress-container">
        <div class="progress-bar" :style="{ width: progressPercent + '%' }" />
      </div>
      <div class="progress-message">
        <span>{{ progressMessage }}</span>
        <strong>{{ displayCompletedCount }} 完成 / {{ displayFailedCount }} 失败 / 共 {{ displayTotalCount }} 张</strong>
      </div>

      <div class="progress-steps">
        <div
          v-for="image in store.images"
          :key="`step-${image.index}`"
          class="progress-step"
          :class="image.status"
          :title="`Page ${image.index + 1}：${getStatusText(image.status)}`"
        >
          P{{ image.index + 1 }}
        </div>
      </div>

      <div v-if="error" class="error-msg">
        {{ error }}
      </div>
      <div v-else-if="firstFailureReason" class="error-msg">
        {{ firstFailureReason }}
      </div>

      <div class="grid-cols-4" style="margin-top: 40px;">
        <div v-for="image in store.images" :key="image.index" class="image-card">
          <!-- 图片展示区域 -->
          <div v-if="image.url && image.status === 'done'" class="image-preview">
            <img :src="image.url" :alt="`第 ${image.index + 1} 页`" />
            <div class="hover-preview">
              <img :src="getFullImageUrl(image.url)" :alt="`第 ${image.index + 1} 页大图预览`" />
            </div>
            <!-- 重新生成按钮（悬停显示） -->
            <div class="image-overlay">
              <button
                class="overlay-btn"
                @click="regenerateImage(image.index)"
                :disabled="image.status === 'retrying'"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M23 4v6h-6"></path>
                  <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
                </svg>
                重新生成
              </button>
            </div>
          </div>

          <!-- 生成中/重试中状态 -->
          <div v-else-if="image.status === 'generating' || image.status === 'retrying'" class="image-placeholder">
            <div class="spinner"></div>
            <div class="status-text">{{ image.status === 'retrying' ? '重试中...' : '生成中...' }}</div>
          </div>

          <!-- 失败状态 -->
          <div v-else-if="image.status === 'error'" class="image-placeholder error-placeholder">
            <div class="error-icon">!</div>
            <div class="status-text">生成失败</div>
            <div v-if="image.error" class="image-error-detail" :title="image.error">
              {{ simplifyError(image.error) }}
            </div>
            <button
              class="retry-btn"
              @click="retrySingleImage(image.index)"
              :disabled="isRetrying"
            >
              点击重试
            </button>
          </div>

          <!-- 等待中状态 -->
          <div v-else class="image-placeholder">
            <div class="status-text">等待中</div>
          </div>

          <!-- 底部信息栏 -->
          <div class="image-footer">
            <span class="page-label">Page {{ image.index + 1 }}</span>
            <span class="status-badge" :class="image.status">
              {{ getStatusText(image.status) }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useGeneratorStore } from '../stores/generator'
import { useAuthStore } from '../stores/auth'
import { generateImagesPost, regenerateImage as apiRegenerateImage, retryFailedImages as apiRetryFailed, updateHistory, getHistory, getImageUrl, withAuthUrl } from '../api'
import { useDraftAutosave } from '../composables/useDraftAutosave'

const router = useRouter()
const store = useGeneratorStore()
const auth = useAuthStore()
const { ensureDraftSaved } = useDraftAutosave({ watchOutline: false })

const error = ref('')
const isRetrying = ref(false)
const redirectTimer = ref<number | null>(null)
const regeneratingIndices = ref(new Set<number>())
const visualProgress = ref(0)
const progressMessage = ref('准备生成图片')
const progressPhase = ref('准备中')
const retryProgressActive = ref(false)
const retryHandledCount = ref(0)
const retryFailedCount = ref(0)
const retryTotalCount = ref(0)
let isUnmounted = false
let progressTimer: number | null = null

const isSingleMode = computed(() => router.currentRoute.value.query.mode === 'single')
const isPageMode = computed(() => router.currentRoute.value.query.mode === 'page')
const isSelectedMode = computed(() => router.currentRoute.value.query.mode === 'selected')
const qualityMode = computed<'fast' | 'fine'>(() => {
  return router.currentRoute.value.query.quality === 'fine' ? 'fine' : 'fast'
})
const selectedPageIndex = computed(() => {
  const raw = router.currentRoute.value.query.page
  const value = Array.isArray(raw) ? raw[0] : raw
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
})
const selectedPageIndexes = computed(() => {
  const raw = router.currentRoute.value.query.pages
  const value = Array.isArray(raw) ? raw[0] : raw
  if (!value) return []
  return value
    .split(',')
    .map(item => Number(item))
    .filter(item => Number.isFinite(item))
})

const pagesToGenerate = computed(() => {
  if (isSelectedMode.value) {
    const selected = new Set(selectedPageIndexes.value)
    return store.outline.pages.filter(page => selected.has(page.index))
  }
  if (isPageMode.value && selectedPageIndex.value !== null) {
    const selectedPage = store.outline.pages.find(page => page.index === selectedPageIndex.value)
    return selectedPage ? [selectedPage] : []
  }
  if (!isSingleMode.value) return store.outline.pages
  const coverPage = store.outline.pages.find(page => page.type === 'cover')
  return coverPage ? [coverPage] : store.outline.pages.slice(0, 1)
})

const isGenerating = computed(() => store.progress.status === 'generating')

const generationSubtitle = computed(() => {
  if (isSelectedMode.value) {
    return `正在生成已选 ${pagesToGenerate.value.length} 张图片`
  }
  if (isPageMode.value && pagesToGenerate.value[0]) {
    return `正在生成第 ${pagesToGenerate.value[0].index + 1} 页图片`
  }
  if (isSingleMode.value) return '正在生成 1 张预览图'
  if (qualityMode.value === 'fast') return `快速并发生成 ${store.progress.total} 张图片`
  return `正在生成第 ${store.progress.current + 1} / ${store.progress.total} 页`
})

const generationDoneSubtitle = computed(() => {
  if (isSelectedMode.value) {
    return `已选 ${pagesToGenerate.value.length} 张图片生成完成`
  }
  if (isPageMode.value && pagesToGenerate.value[0]) {
    return `第 ${pagesToGenerate.value[0].index + 1} 页图片生成完成`
  }
  if (isSingleMode.value) return '1 张预览图生成完成'
  return `全部 ${store.progress.total} 张图片生成完成`
})

const progressPercent = computed(() => {
  if (retryProgressActive.value) {
    if (retryTotalCount.value === 0) return 0
    const retryProgress = (retryHandledCount.value / retryTotalCount.value) * 100
    return Math.min(100, Math.max(retryProgress, visualProgress.value))
  }
  if (store.progress.total === 0) return 0
  const realProgress = (handledCount.value / store.progress.total) * 100
  return Math.min(100, Math.max(realProgress, visualProgress.value))
})

const hasFailedImages = computed(() => store.images.some(img => img.status === 'error'))

const completedCount = computed(() => store.images.filter(img => img.status === 'done').length)

const failedCount = computed(() => store.images.filter(img => img.status === 'error').length)

const handledCount = computed(() => completedCount.value + failedCount.value)

const displayCompletedCount = computed(() => {
  if (!retryProgressActive.value) return completedCount.value
  return retryHandledCount.value - retryFailedCount.value
})

const displayFailedCount = computed(() => {
  if (!retryProgressActive.value) return failedCount.value
  return retryFailedCount.value
})

const displayTotalCount = computed(() => {
  if (!retryProgressActive.value) return store.progress.total
  return retryTotalCount.value
})

const firstFailureReason = computed(() => {
  const failed = store.images.find(img => img.status === 'error' && img.error)
  if (!failed?.error) return ''
  return `图片生成失败：${simplifyError(failed.error)}`
})

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    generating: '生成中',
    done: '已完成',
    error: '失败',
    retrying: '重试中'
  }
  return texts[status] || '等待中'
}

const getFullImageUrl = (url: string) => {
  const baseUrl = url.split('?')[0]
  return withAuthUrl(`${baseUrl}?thumbnail=false`)
}

const filenameFromImageUrl = (url: string) => {
  const cleanUrl = url.split('?')[0]
  return cleanUrl.split('/').pop() || ''
}

const createEmptyImageSlots = () => Array.from({ length: store.outline.pages.length }, () => '')

async function getExistingGeneratedImages() {
  if (!store.recordId) return createEmptyImageSlots()

  try {
    const result = await getHistory(store.recordId)
    const existing = result.record?.images?.generated || []
    const slots = createEmptyImageSlots()
    existing.forEach((filename, index) => {
      if (filename) slots[index] = filename
    })
    return slots
  } catch (e) {
    console.error('读取历史图片列表失败:', e)
    return createEmptyImageSlots()
  }
}

async function ensureHistoryTaskId() {
  if (!store.recordId) return

  try {
    const result = await getHistory(store.recordId)
    const taskId = result.record?.images?.task_id || null
    if (taskId) {
      store.taskId = taskId
    } else {
      store.taskId = null
    }
  } catch (e) {
    console.error('读取历史任务 ID 失败:', e)
  }
}

async function saveGenerationToHistory(taskId: string) {
  if (!store.recordId) return

  const generatedImages = await getExistingGeneratedImages()
  store.images.forEach(image => {
    if (image.status === 'done' && image.url) {
      generatedImages[image.index] = filenameFromImageUrl(image.url)
    }
  })

  const generatedCount = generatedImages.filter(Boolean).length
  const status = generatedCount === 0
    ? 'draft'
    : generatedCount >= store.outline.pages.length
      ? 'completed'
      : 'partial'
  const thumbnail = generatedImages.find(Boolean) || null

  await updateHistory(store.recordId, {
    images: {
      task_id: taskId,
      generated: generatedImages
    },
    status,
    thumbnail
  })
}

const simplifyError = (message: string) => {
  if (!message) return '请检查图片服务配置后重试'
  if (message.includes('ProxyError') || message.includes('Unable to connect to proxy')) {
    return '代理连接失败，后端无法连到图片接口。请检查代理是否允许 Python/终端访问，或重启后端后重试。'
  }
  if (message.includes('401') || message.includes('认证失败')) {
    return 'API Key 认证失败，请检查图片服务商密钥。'
  }
  if (message.includes('429') || message.includes('rate')) {
    return '接口限流或额度不足，请稍后重试或检查额度。'
  }
  if (message.includes('404')) {
    return '图片接口地址或模型不正确，请检查 Base URL、端点和模型名。'
  }
  if (message.includes('timeout') || message.includes('超时')) {
    return '图片接口响应超时，请稍后重试或降低一次生成页数。'
  }
  return message.length > 110 ? `${message.slice(0, 110)}...` : message
}

function startVisualProgress() {
  stopVisualProgress()
  retryProgressActive.value = false
  retryHandledCount.value = 0
  retryFailedCount.value = 0
  retryTotalCount.value = 0
  visualProgress.value = 8
  progressPhase.value = '连接服务'
  progressMessage.value = '正在连接图片生成服务'

  progressTimer = window.setInterval(() => {
    const cap = store.progress.total <= 1 ? 92 : 88
    const next = Math.min(visualProgress.value + Math.max(1, Math.round(Math.random() * 4)), cap)
    visualProgress.value = next

    if (next >= 70) {
      progressPhase.value = '等待结果'
      progressMessage.value = '正在等待图片返回'
    } else if (next >= 42) {
      progressPhase.value = '生成图片'
      progressMessage.value = '正在生成画面细节'
    } else if (next >= 20) {
      progressPhase.value = '提交任务'
      progressMessage.value = '正在提交图片提示词'
    }
  }, 900)
}

function syncVisualProgress() {
  if (store.progress.total === 0) return
  const realProgress = (handledCount.value / store.progress.total) * 100
  visualProgress.value = Math.max(visualProgress.value, realProgress)
  if (handledCount.value >= store.progress.total) {
    progressPhase.value = failedCount.value > 0 ? '生成结束' : '生成完成'
    progressMessage.value = failedCount.value > 0 ? '图片生成结束，部分图片失败' : '图片生成完成'
  } else {
    progressPhase.value = '生成图片'
    progressMessage.value = '已处理部分图片，继续生成中'
  }
}

function finishVisualProgress(success: boolean) {
  stopVisualProgress()
  if (success) {
    visualProgress.value = 100
    progressPhase.value = '生成完成'
    progressMessage.value = '图片生成完成'
  } else {
    const finalProgress = retryProgressActive.value && retryTotalCount.value > 0
      ? (retryHandledCount.value / retryTotalCount.value) * 100
      : store.progress.total > 0
        ? (handledCount.value / store.progress.total) * 100
        : visualProgress.value
    visualProgress.value = Math.max(visualProgress.value, finalProgress)
    progressPhase.value = '生成结束'
    progressMessage.value = '部分图片生成失败，可查看错误后重试'
  }
}

function stopVisualProgress() {
  if (progressTimer !== null) {
    clearInterval(progressTimer)
    progressTimer = null
  }
}

function resetRetryProgress(total: number, message: string) {
  stopVisualProgress()
  error.value = ''
  retryProgressActive.value = true
  retryHandledCount.value = 0
  retryFailedCount.value = 0
  retryTotalCount.value = total
  store.progress.current = 0
  store.progress.total = total
  store.progress.status = 'generating'
  visualProgress.value = 8
  progressPhase.value = '重试中'
  progressMessage.value = message

  progressTimer = window.setInterval(() => {
    const next = Math.min(visualProgress.value + Math.max(1, Math.round(Math.random() * 4)), 92)
    visualProgress.value = next
    if (next >= 70) {
      progressMessage.value = '正在等待重试结果'
    } else if (next >= 35) {
      progressMessage.value = '正在重新生成图片'
    }
  }, 900)
}

// 重试单张图片（异步并发执行，不阻塞）
function retrySingleImage(index: number) {
  if (!store.taskId || regeneratingIndices.value.has(index)) return

  const page = store.outline.pages.find(p => p.index === index)
  if (!page) return

  // 标记为正在重绘
  regeneratingIndices.value.add(index)
  resetRetryProgress(1, `正在重试第 ${index + 1} 页`)

  // 立即设置为重试状态
  store.setImageRetrying(index)

  // 构建上下文信息
  const context = {
    fullOutline: store.outline.raw || '',
    userTopic: store.topic || ''
  }

  // 异步执行重绘，不阻塞
  apiRegenerateImage(store.taskId, page, true, context)
    .then(result => {
      if (result.success && result.image_url) {
        store.updateImage(index, result.image_url)
        retryHandledCount.value = 1
        finishVisualProgress(true)
        saveGenerationToHistory(store.taskId!)
      } else {
        error.value = result.error ? `第 ${index + 1} 页生成失败：${simplifyError(result.error)}` : '图片生成失败'
        store.updateProgress(index, 'error', undefined, result.error)
        retryHandledCount.value = 1
        retryFailedCount.value = 1
        finishVisualProgress(false)
      }
    })
    .catch(e => {
      const message = String(e)
      error.value = `第 ${index + 1} 页生成失败：${simplifyError(message)}`
      store.updateProgress(index, 'error', undefined, message)
      retryHandledCount.value = 1
      retryFailedCount.value = 1
      finishVisualProgress(false)
    })
    .finally(() => {
      regeneratingIndices.value.delete(index)
      store.progress.status = hasFailedImages.value ? 'error' : 'done'
      auth.refreshUser()
    })
}

// 重新生成图片（成功的也可以重新生成，立即返回不等待）
function regenerateImage(index: number) {
  retrySingleImage(index)
}

// 批量重试所有失败的图片
async function retryAllFailed() {
  if (!store.taskId) return

  const failedPages = store.getFailedPages()
  if (failedPages.length === 0) return

  isRetrying.value = true
  resetRetryProgress(failedPages.length, `正在补全 ${failedPages.length} 张失败图片`)

  // 设置所有失败的图片为重试状态
  failedPages.forEach(page => {
    store.setImageRetrying(page.index)
  })

  try {
    await apiRetryFailed(
      store.taskId,
      failedPages,
      // onProgress
      (event) => {
        progressPhase.value = '批量重试'
        progressMessage.value = event.message || '正在补全失败图片'
      },
      // onComplete
      (event) => {
        if (event.image_url) {
          store.updateImage(event.index, event.image_url)
          retryHandledCount.value += 1
          syncVisualProgress()
        }
      },
      // onError
      (event) => {
        error.value = event.message ? `第 ${event.index + 1} 页生成失败：${simplifyError(event.message)}` : '图片生成失败'
        store.updateProgress(event.index, 'error', undefined, event.message)
        retryHandledCount.value += 1
        retryFailedCount.value += 1
        syncVisualProgress()
      },
      // onFinish
      async (event) => {
        isRetrying.value = false
        finishVisualProgress(event.success)
        store.progress.status = hasFailedImages.value ? 'error' : 'done'
        if (store.taskId) {
          await saveGenerationToHistory(store.taskId)
        }
        await auth.refreshUser()
      },
      // onStreamError
      (err) => {
        console.error('重试失败:', err)
        isRetrying.value = false
        finishVisualProgress(false)
        store.progress.status = 'error'
        error.value = '重试失败: ' + err.message
        auth.refreshUser()
      }
    )
  } catch (e) {
    isRetrying.value = false
    finishVisualProgress(false)
    store.progress.status = 'error'
    error.value = '重试失败: ' + String(e)
    await auth.refreshUser()
  }
}

onMounted(async () => {
  if (store.outline.pages.length === 0) {
    router.push('/')
    return
  }

  // 历史记录处理逻辑：
  // 正常情况下，recordId 应该在大纲生成页（OutlineView）创建
  // 这里根据 recordId 是否存在做不同处理
  if (store.recordId) {
    // 情况1：recordId 已存在（正常流程）
    // 更新历史记录状态为 generating，表示图片生成已开始
    try {
      await updateHistory(store.recordId, { status: 'generating' })
      console.log('历史记录状态已更新为 generating:', store.recordId)
    } catch (e) {
      // 更新失败不阻断生成流程，仅记录错误
      console.error('更新历史记录状态失败:', e)
    }
  } else {
    // 情况2：recordId 不存在（异常情况）
    // 这种情况不应该发生，但作为兜底逻辑，尝试创建历史记录
    console.warn('警告: recordId 不存在，尝试创建历史记录作为兜底')
    const saved = await ensureDraftSaved()
    if (!saved) {
      console.error('兜底创建历史记录失败')
    }
  }

  const targetPages = pagesToGenerate.value
  if (targetPages.length === 0) {
    router.push('/outline')
    return
  }

  await ensureHistoryTaskId()
  store.startGeneration(targetPages)
  startVisualProgress()

  generateImagesPost(
    targetPages,
    store.taskId,
    store.outline.raw,  // 传入完整大纲文本
    // onProgress
    (event) => {
      console.log('Progress:', event)
      progressPhase.value = event.phase === 'cover' ? '生成封面' : '生成内容'
      if (event.message) {
        progressMessage.value = event.message
      } else if (event.status === 'generating') {
        progressMessage.value = (isSingleMode.value || isPageMode.value || isSelectedMode.value) ? generationSubtitle.value : `正在生成第 ${event.index + 1} 页`
      }
    },
    // onComplete
    (event) => {
      console.log('Complete:', event)
      if (event.image_url) {
        store.updateProgress(event.index, 'done', event.image_url)
        syncVisualProgress()
      }
    },
    // onError
    (event) => {
      console.error('Error:', event)
      error.value = event.message ? `第 ${event.index + 1} 页生成失败：${simplifyError(event.message)}` : '图片生成失败'
      store.updateProgress(event.index, 'error', undefined, event.message)
      syncVisualProgress()
    },
    // onFinish
    async (event) => {
      console.log('Finish:', event)
      finishVisualProgress(event.success)
      store.taskId = event.task_id
      store.finishGeneration(event.task_id)

      // 更新历史记录
      if (store.recordId) {
        try {
          await saveGenerationToHistory(event.task_id)
          console.log('历史记录已更新')
        } catch (e) {
          console.error('更新历史记录失败:', e)
        }
      }

      // 如果没有失败的，跳转到结果页
      if (!hasFailedImages.value) {
        redirectTimer.value = window.setTimeout(() => {
          if (!isUnmounted) {
            router.push('/result')
          }
        }, 1000)
      }
      await auth.refreshUser()
    },
    // onStreamError
    (err) => {
      console.error('Stream Error:', err)
      finishVisualProgress(false)
      error.value = '生成失败: ' + err.message
      auth.refreshUser()
    },
    // userImages - 用户上传的参考图片
    store.userImages.length > 0 ? store.userImages : undefined,
    // userTopic - 用户原始输入
    store.topic,
    qualityMode.value
  )
})

onUnmounted(() => {
  isUnmounted = true
  stopVisualProgress()
  if (redirectTimer.value !== null) {
    clearTimeout(redirectTimer.value)
    redirectTimer.value = null
  }
})
</script>

<style scoped>
.image-preview {
  aspect-ratio: 3/4;
  overflow: visible;
  position: relative;
  flex: 1; /* 填充卡片剩余空间 */
}

.progress-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  margin-bottom: 14px;
}

.progress-head span,
.progress-head strong {
  display: block;
}

.progress-head span {
  color: #222;
  font-weight: 700;
}

.progress-head strong {
  margin-top: 4px;
  color: var(--text-sub);
  font-size: 13px;
  font-weight: 500;
}

.progress-head em {
  color: var(--primary);
  font-size: 24px;
  font-style: normal;
  font-weight: 800;
}

.progress-message {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: center;
  margin-top: 10px;
  color: var(--text-sub);
  font-size: 13px;
}

.progress-message strong {
  flex: 0 0 auto;
  color: #6f6265;
  font-weight: 700;
}

.progress-steps {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
}

.progress-step {
  display: grid;
  place-items: center;
  min-width: 40px;
  height: 28px;
  padding: 0 10px;
  border: 1px solid #ececec;
  border-radius: 999px;
  background: #fafafa;
  color: #999;
  font-size: 12px;
  font-weight: 800;
}

.progress-step.generating,
.progress-step.retrying {
  border-color: #b8dcff;
  background: #eef7ff;
  color: #1890ff;
}

.progress-step.done {
  border-color: #bce8c8;
  background: #effaf2;
  color: #2f9f4a;
}

.progress-step.error {
  border-color: #ffc3c1;
  background: #fff1f0;
  color: #e33b3b;
}

@media (max-width: 640px) {
  .progress-message {
    display: grid;
  }

  .progress-message strong {
    flex: auto;
  }
}

.image-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-preview > img {
  border-radius: 0;
}

.hover-preview {
  position: absolute;
  left: calc(100% + 14px);
  top: 50%;
  z-index: 80;
  width: min(360px, 58vw);
  aspect-ratio: 3/4;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.9);
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 24px 70px rgba(26, 20, 20, 0.24);
  opacity: 0;
  pointer-events: none;
  transform: translateY(-50%) scale(0.96);
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.image-card:nth-child(4n) .hover-preview,
.image-card:nth-child(4n - 1) .hover-preview {
  left: auto;
  right: calc(100% + 14px);
}

.hover-preview img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #fff;
}

.image-preview:hover .hover-preview {
  opacity: 1;
  transform: translateY(-50%) scale(1);
}

.image-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
}

.image-preview:hover .image-overlay {
  opacity: 1;
}

.overlay-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #333;
  transition: all 0.2s;
}

.overlay-btn:hover {
  background: var(--primary);
  color: white;
}

.overlay-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.image-placeholder {
  aspect-ratio: 3/4;
  background: #f9f9f9;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  flex: 1; /* 填充卡片剩余空间 */
  min-height: 240px; /* 确保有最小高度 */
}

.error-placeholder {
  background: #fff5f5;
}

.error-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #ff4d4f;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: bold;
}

.status-text {
  font-size: 13px;
  color: var(--text-sub);
}

.image-error-detail {
  display: -webkit-box;
  max-width: 86%;
  overflow: hidden;
  color: #d92d42;
  font-size: 12px;
  line-height: 1.5;
  text-align: center;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}

.retry-btn {
  margin-top: 8px;
  padding: 6px 16px;
  background: var(--primary);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.retry-btn:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

.retry-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.image-footer {
  padding: 12px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-label {
  font-size: 12px;
  color: var(--text-sub);
}

.status-badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
}

.status-badge.done {
  background: #E6F7ED;
  color: #52C41A;
}

.status-badge.generating,
.status-badge.retrying {
  background: #E6F4FF;
  color: #1890FF;
}

.status-badge.error {
  background: #FFF1F0;
  color: #FF4D4F;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--primary);
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
