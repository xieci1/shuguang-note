<template>
  <div class="container task-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">任务中心</h1>
        <p class="page-subtitle">
          {{ auth.isAdmin ? '查看所有用户的任务进度、失败数量和关联作品。' : '查看你的任务进度、失败数量和关联作品。' }}
        </p>
      </div>
      <button class="btn refresh-btn" @click="loadTasks" :disabled="loading">
        {{ loading ? '刷新中...' : '刷新' }}
      </button>
    </div>

    <section class="task-summary">
      <div>
        <span>发布任务</span>
        <strong>{{ publishJobs.length }}</strong>
      </div>
      <div>
        <span>图片任务</span>
        <strong>{{ tasks.length }}</strong>
      </div>
      <div>
        <span>进行中</span>
        <strong>{{ runningCount }}</strong>
      </div>
      <div>
        <span>异常</span>
        <strong>{{ failedCount }}</strong>
      </div>
    </section>

    <section class="task-section">
      <div class="task-section-header">
        <div>
          <h2>发布任务</h2>
          <p>{{ auth.isAdmin ? '查看所有小红书发布任务，日志默认收起。' : '查看你的小红书发布任务，日志默认收起。' }}</p>
        </div>
      </div>

      <div v-if="publishJobs.length === 0 && !loading" class="empty-inline">
        暂无发布任务。
      </div>

      <div v-else class="task-list">
        <article v-for="job in publishJobs" :key="job.id" class="task-row publish-row">
          <div class="task-main">
            <div class="task-title-line">
              <strong>{{ job.draft_title || '小红书发布任务' }}</strong>
              <span class="task-status" :class="job.status">{{ getPublishStatusText(job.status) }}</span>
            </div>
            <div class="task-meta">
              <span v-if="auth.isAdmin">{{ job.user?.name || '未知用户' }}</span>
              <span>{{ job.account_name || '未知账号' }}</span>
              <span>{{ formatDate(job.updated_at) }}</span>
            </div>
            <p v-if="job.error" class="task-error">{{ job.error }}</p>
            <div v-if="job.logs" class="log-panel">
              <div class="log-summary">
                <span>{{ summarizeLog(job.logs) }}</span>
                <button type="button" @click="toggleLog(job.id)">
                  {{ expandedLogs.has(job.id) ? '收起日志' : '查看日志' }}
                </button>
              </div>
              <pre v-if="expandedLogs.has(job.id)" class="task-logs">{{ formatLog(job.logs) }}</pre>
            </div>
          </div>

          <button
            class="task-action"
            :disabled="!job.creation_id"
            @click="openRecord(job.creation_id || null)"
          >
            查看作品
          </button>
        </article>
      </div>
    </section>

    <section class="task-section">
      <div class="task-section-header">
        <div>
          <h2>图片任务</h2>
          <p>查看最近图片生成任务的进度、失败数量和关联作品。</p>
        </div>
      </div>

      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
      </div>

      <div v-else-if="tasks.length === 0" class="empty-state-large">
        <h3>暂无生成任务</h3>
        <p>开始生成图片后，任务会出现在这里。</p>
      </div>

      <div v-else class="image-task-grid">
        <article v-for="task in tasks" :key="task.task_id" class="image-task-card">
          <div class="image-task-head">
            <div>
              <strong>{{ task.title }}</strong>
              <span>{{ shortTaskId(task.task_id) }} · {{ formatDate(task.updated_at) }}</span>
            </div>
            <span class="task-status" :class="task.status">{{ getStatusText(task.status) }}</span>
          </div>

          <div class="task-progress">
            <div class="task-progress-bar" :style="{ width: getProgress(task) + '%' }"></div>
          </div>

          <div class="task-counts">
            <strong>{{ getProgress(task) }}%</strong>
            <span>{{ task.completed }} 完成</span>
            <span>{{ task.failed }} 失败</span>
            <span>共 {{ task.total }} 张</span>
          </div>

          <p v-if="task.error" class="task-error">{{ task.error }}</p>

          <button
            class="task-action"
            :disabled="!task.creation_id"
            @click="openRecord(task.creation_id)"
          >
            查看作品
          </button>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getPublishJobs, getTaskList, type ImageTaskItem, type PublishJob } from '../api'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)
const tasks = ref<ImageTaskItem[]>([])
const publishJobs = ref<PublishJob[]>([])
const expandedLogs = ref(new Set<string>())

const runningCount = computed(() => {
  return publishJobs.value.filter(job => ['queued', 'running'].includes(job.status)).length
    + tasks.value.filter(task => task.status === 'generating').length
})

const failedCount = computed(() => {
  return publishJobs.value.filter(job => ['failed', 'cancelled'].includes(job.status)).length
    + tasks.value.filter(task => task.status === 'error' || task.failed > 0).length
})

async function loadTasks() {
  loading.value = true
  try {
    const [taskResult, publishResult] = await Promise.all([
      getTaskList(50),
      getPublishJobs(20)
    ])
    tasks.value = taskResult.success ? taskResult.tasks : []
    publishJobs.value = publishResult.success ? publishResult.jobs : []
  } catch (e) {
    console.error('加载任务失败:', e)
    tasks.value = []
    publishJobs.value = []
  } finally {
    loading.value = false
  }
}

function getProgress(task: ImageTaskItem) {
  if (!task.total) return 0
  return Math.min(100, Math.round(((task.completed + task.failed) / task.total) * 100))
}

function getStatusText(status: string) {
  const names: Record<string, string> = {
    draft: '草稿',
    generating: '生成中',
    partial: '部分完成',
    completed: '已完成',
    error: '失败'
  }
  return names[status] || status
}

function getPublishStatusText(status: string) {
  const names: Record<string, string> = {
    queued: '排队中',
    running: '发布中',
    ready_for_review: '已发布',
    failed: '失败',
    cancelled: '已取消'
  }
  return names[status] || status
}

function shortTaskId(value: string) {
  return value.length > 14 ? `${value.slice(0, 12)}...` : value
}

function toggleLog(jobId: string) {
  const next = new Set(expandedLogs.value)
  if (next.has(jobId)) next.delete(jobId)
  else next.add(jobId)
  expandedLogs.value = next
}

function summarizeLog(logs: string) {
  const parsed = parseJsonLog(logs)
  if (parsed?.message) return String(parsed.message)
  if (parsed?.error) return String(parsed.error)
  const clean = logs.replace(/\s+/g, ' ').trim()
  return clean.length > 120 ? `${clean.slice(0, 120)}...` : clean || '暂无日志摘要'
}

function formatLog(logs: string) {
  const parsed = parseJsonLog(logs)
  if (parsed) return JSON.stringify(parsed, null, 2)
  return logs
}

function parseJsonLog(logs: string) {
  const value = String(logs || '').trim()
  if (!value.startsWith('{') && !value.startsWith('[')) return null
  try {
    return JSON.parse(value)
  } catch {
    return null
  }
}

function formatDate(value: string) {
  const d = new Date(value)
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function openRecord(recordId: string | null) {
  if (!recordId) return
  router.push(`/history/${recordId}`)
}

onMounted(loadTasks)
</script>

<style scoped>
.task-page {
  max-width: 1180px;
}

.refresh-btn {
  min-height: 44px;
  border: 1px solid var(--border-color);
  background: #fff;
  color: #2b2022;
  box-shadow: 0 8px 18px rgba(33, 20, 20, 0.04);
}

.task-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 24px;
}

.task-summary div {
  display: grid;
  gap: 4px;
  padding: 18px;
  border: 1px solid #f1eeee;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 12px 28px rgba(33, 20, 20, 0.04);
}

.task-summary span {
  color: #8a6e73;
  font-size: 13px;
  font-weight: 800;
}

.task-summary strong {
  color: #241d1f;
  font-size: 28px;
  line-height: 1.1;
}

.task-list {
  display: grid;
  gap: 12px;
}

.task-section {
  margin-bottom: 30px;
}

.task-section-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.task-section-header h2 {
  margin: 0 0 4px;
  color: #241d1f;
  font-size: 22px;
}

.task-section-header p {
  margin: 0;
  color: #8a6e73;
  font-size: 14px;
}

.empty-inline {
  padding: 18px;
  border: 1px solid #f1eeee;
  border-radius: 14px;
  background: #fff;
  color: #8a6e73;
}

.task-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 18px;
  align-items: center;
  padding: 18px;
  border: 1px solid #f1eeee;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(33, 20, 20, 0.04);
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

.task-row:hover,
.image-task-card:hover {
  border-color: #f3d8dd;
  box-shadow: 0 14px 34px rgba(33, 20, 20, 0.06);
}

.task-main {
  min-width: 0;
}

.task-title-line {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 6px;
}

.task-title-line strong {
  min-width: 0;
  overflow: hidden;
  color: #2b2022;
  font-size: 16px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-status {
  flex: 0 0 auto;
  padding: 2px 8px;
  border-radius: 999px;
  background: #f5f5f5;
  color: #666;
  font-size: 12px;
  font-weight: 800;
}

.task-status.completed {
  background: #f6ffed;
  color: #2f7a16;
}

.task-status.generating,
.task-status.partial {
  background: #e6f7ff;
  color: #1769aa;
}

.task-status.error {
  background: #fff5f5;
  color: #b42318;
}

.task-status.ready_for_review {
  background: #fff8e6;
  color: #9a6400;
}

.task-status.running,
.task-status.queued {
  background: #e6f7ff;
  color: #1769aa;
}

.task-status.failed,
.task-status.cancelled {
  background: #fff5f5;
  color: #b42318;
}

.task-meta,
.task-counts {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  color: #8a6e73;
  font-size: 12px;
}

.log-panel {
  margin-top: 12px;
  border: 1px solid #f1eeee;
  border-radius: 12px;
  background: #fafafa;
  overflow: hidden;
}

.log-summary {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
}

.log-summary span {
  min-width: 0;
  overflow: hidden;
  color: #716469;
  font-size: 12px;
  line-height: 1.5;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.log-summary button {
  flex: 0 0 auto;
  min-height: 30px;
  padding: 0 10px;
  border: 1px solid #f2dce0;
  border-radius: 999px;
  background: #fff;
  color: #ff2442;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}

.image-task-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 14px;
}

.image-task-card {
  display: grid;
  gap: 14px;
  align-content: start;
  padding: 18px;
  border: 1px solid #f1eeee;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(33, 20, 20, 0.04);
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

.image-task-head {
  display: flex;
  gap: 12px;
  justify-content: space-between;
}

.image-task-head div {
  display: grid;
  gap: 5px;
  min-width: 0;
}

.image-task-head strong {
  min-width: 0;
  overflow: hidden;
  color: #2b2022;
  font-size: 16px;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.image-task-head div > span {
  color: #8a6e73;
  font-size: 12px;
}

.task-progress {
  height: 8px;
  margin: 2px 0 0;
  overflow: hidden;
  border-radius: 999px;
  background: #f5eef0;
}

.task-progress-bar {
  height: 100%;
  border-radius: inherit;
  background: #ff2442;
  transition: width 0.25s ease;
}

.task-error {
  margin-top: 8px;
  color: #b42318;
  font-size: 12px;
  line-height: 1.5;
}

.task-logs {
  max-height: 180px;
  overflow: auto;
  margin: 0;
  padding: 12px;
  border-top: 1px solid #f1eeee;
  background: #fff;
  color: #62565a;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-word;
}

.task-counts {
  align-items: center;
}

.task-counts strong {
  color: #ff2442;
  font-size: 18px;
}

.task-action {
  min-height: 42px;
  padding: 0 18px;
  border: none;
  border-radius: 999px;
  background: #ff2442;
  color: #fff;
  font-weight: 900;
  cursor: pointer;
  white-space: nowrap;
  box-shadow: 0 10px 22px rgba(255, 36, 66, 0.18);
}

.task-action:disabled {
  opacity: 0.42;
  cursor: not-allowed;
  box-shadow: none;
}

@media (max-width: 860px) {
  .task-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .task-row {
    display: grid;
    grid-template-columns: 1fr;
  }

  .task-action {
    width: max-content;
  }
}

@media (max-width: 560px) {
  .task-summary,
  .image-task-grid {
    grid-template-columns: 1fr;
  }

  .log-summary {
    display: grid;
  }

  .task-action {
    width: 100%;
  }
}
</style>
