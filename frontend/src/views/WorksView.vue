<template>
  <div class="container works-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">作品管理</h1>
        <p class="page-subtitle">按用户查看生成内容、图片和发布前素材。</p>
      </div>
      <button class="btn" @click="loadData" :disabled="loading">
        {{ loading ? '刷新中...' : '刷新' }}
      </button>
    </div>

    <section class="filter-bar">
      <label>
        <span>用户</span>
        <select v-model="selectedUserId" @change="applyFilters">
          <option value="">全部用户</option>
          <option v-for="user in users" :key="user.id" :value="user.id">
            {{ user.name }} · {{ user.email }}
          </option>
        </select>
      </label>
      <label>
        <span>状态</span>
        <select v-model="selectedStatus" @change="applyFilters">
          <option value="">全部状态</option>
          <option value="completed">已完成</option>
          <option value="published">已发布</option>
          <option value="draft">草稿</option>
          <option value="partial">部分完成</option>
          <option value="error">失败</option>
        </select>
      </label>
      <div class="summary">
        <strong>{{ totalCount }}</strong>
        <span>条作品</span>
      </div>
    </section>

    <section class="table-panel">
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
      </div>
      <div v-else-if="records.length === 0" class="empty-panel">暂无作品。</div>
      <table v-else class="works-table">
        <thead>
          <tr>
            <th>作品</th>
            <th>作者</th>
            <th>生成日期</th>
            <th>页数</th>
            <th>状态</th>
            <th>素材</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="record in records" :key="record.id">
            <td>
              <div class="work-cell">
                <div class="thumb">
                  <img v-if="record.thumbnail && record.task_id" :src="getImageUrl(record.task_id, record.thumbnail)" alt="" />
                  <span v-else>{{ record.title.charAt(0) }}</span>
                </div>
                <strong>{{ record.title }}</strong>
              </div>
            </td>
            <td>{{ record.user?.name || '未绑定用户' }}</td>
            <td>{{ formatDateTime(record.created_at) }}</td>
            <td>{{ record.page_count }}P</td>
            <td><span class="status-pill" :class="record.status">{{ statusText(record) }}</span></td>
            <td>{{ record.thumbnail ? '有图片' : '无封面' }}</td>
            <td class="actions">
              <button type="button" @click="openDetail(record)">查看</button>
              <button type="button" @click="openHistory(record.id)">打开</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="totalPages > 1" class="pagination">
        <button :disabled="currentPage === 1" @click="changePage(currentPage - 1)">上一页</button>
        <span>{{ currentPage }} / {{ totalPages }}</span>
        <button :disabled="currentPage === totalPages" @click="changePage(currentPage + 1)">下一页</button>
      </div>
    </section>

    <div v-if="detailVisible" class="detail-backdrop" @click.self="closeDetail">
      <section class="detail-drawer">
        <header>
          <div>
            <h2>{{ selectedDetail?.title || '作品详情' }}</h2>
            <p v-if="selectedDetail">
              {{ selectedDetail.user?.name || '未绑定用户' }} · 生成 {{ formatDateTime(selectedDetail.created_at) }}
            </p>
          </div>
          <button class="close-btn" @click="closeDetail">×</button>
        </header>

        <div v-if="detailLoading" class="loading-state">
          <div class="spinner"></div>
        </div>
        <template v-else-if="selectedDetail">
          <div class="content-block">
            <span>标题</span>
            <p>{{ selectedDetail.content?.titles?.join(' / ') || '暂无生成标题' }}</p>
          </div>
          <div class="content-block">
            <span>文案</span>
            <p>{{ selectedDetail.content?.copywriting || '暂无生成文案' }}</p>
          </div>
          <div class="content-block">
            <span>标签</span>
            <div v-if="selectedDetail.content?.tags?.length" class="tag-list">
              <em v-for="tag in selectedDetail.content.tags" :key="tag">#{{ tag }}</em>
            </div>
            <p v-else>暂无标签</p>
          </div>

          <div class="image-grid">
            <div v-for="page in selectedDetail.outline.pages" :key="page.index" class="image-item">
              <img
                v-if="imageFilename(page.index)"
                :src="getImageUrl(selectedDetail.images.task_id || '', imageFilename(page.index))"
                alt=""
              />
              <div v-else>未生成</div>
              <span>P{{ page.index + 1 }}</span>
            </div>
          </div>

          <button class="btn btn-primary detail-open" @click="openHistory(selectedDetail.id)">打开完整作品</button>
        </template>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  getHistory,
  getHistoryList,
  getImageUrl,
  getUsers,
  type HistoryDetail,
  type HistoryRecord,
  type UserItem
} from '../api'

const router = useRouter()
const loading = ref(false)
const detailLoading = ref(false)
const detailVisible = ref(false)
const users = ref<UserItem[]>([])
const records = ref<HistoryRecord[]>([])
const selectedDetail = ref<HistoryDetail | null>(null)
const selectedUserId = ref('')
const selectedStatus = ref('')
const currentPage = ref(1)
const totalPages = ref(1)
const totalCount = ref(0)

async function loadUsers() {
  const result = await getUsers()
  users.value = result.success ? result.users : []
}

async function loadData() {
  loading.value = true
  try {
    const result = await getHistoryList(
      currentPage.value,
      20,
      selectedStatus.value || undefined,
      selectedUserId.value || undefined
    )
    records.value = result.success ? result.records : []
    totalPages.value = result.success ? result.total_pages : 1
    totalCount.value = result.success ? result.total : 0
  } finally {
    loading.value = false
  }
}

async function openDetail(record: HistoryRecord) {
  detailVisible.value = true
  detailLoading.value = true
  selectedDetail.value = null
  try {
    const result = await getHistory(record.id)
    selectedDetail.value = result.success && result.record ? result.record : null
  } finally {
    detailLoading.value = false
  }
}

function closeDetail() {
  detailVisible.value = false
  selectedDetail.value = null
}

function applyFilters() {
  currentPage.value = 1
  loadData()
}

function changePage(page: number) {
  currentPage.value = page
  loadData()
}

function openHistory(id: string) {
  router.push(`/history/${id}`)
}

function imageFilename(index: number) {
  return selectedDetail.value?.images.generated[index] || ''
}

function statusText(record: HistoryRecord) {
  if (record.is_published) return '已发布'
  const names: Record<string, string> = {
    completed: '已完成',
    draft: '草稿',
    generating: '生成中',
    partial: '部分完成',
    error: '失败'
  }
  return names[record.status] || record.status
}

function formatDateTime(value: string) {
  const d = new Date(value)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

onMounted(async () => {
  await Promise.all([loadUsers(), loadData()])
})
</script>

<style scoped>
.works-page {
  max-width: 1280px;
}

.filter-bar,
.table-panel {
  border: 1px solid #f1eeee;
  border-radius: 8px;
  background: #fff;
}

.filter-bar {
  display: flex;
  gap: 14px;
  align-items: end;
  margin-bottom: 16px;
  padding: 14px 16px;
}

.filter-bar label {
  display: grid;
  gap: 6px;
  min-width: 240px;
}

.filter-bar label span {
  color: #8a6e73;
  font-size: 12px;
  font-weight: 800;
}

.filter-bar select {
  min-height: 38px;
  padding: 0 12px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: #fff;
  font: inherit;
}

.summary {
  margin-left: auto;
  text-align: right;
}

.summary strong,
.summary span {
  display: block;
}

.summary strong {
  color: var(--primary);
  font-size: 22px;
}

.summary span {
  color: #8a6e73;
  font-size: 12px;
}

.table-panel {
  overflow: hidden;
}

.works-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.works-table th,
.works-table td {
  padding: 12px 14px;
  border-bottom: 1px solid #f5eeee;
  color: #57484c;
  font-size: 13px;
  vertical-align: middle;
}

.works-table th {
  background: #fff8f9;
  color: #8a6e73;
  font-size: 12px;
  text-align: left;
}

.works-table th:first-child,
.works-table td:first-child {
  width: 42%;
}

.work-cell {
  display: flex;
  gap: 12px;
  align-items: center;
  min-width: 0;
}

.work-cell strong {
  overflow: hidden;
  color: #241d1f;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.thumb {
  display: grid;
  place-items: center;
  flex: 0 0 52px;
  width: 52px;
  aspect-ratio: 3/4;
  overflow: hidden;
  border-radius: 6px;
  background: #f7f8fa;
  color: #c8b6ba;
  font-weight: 900;
}

.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.status-pill {
  display: inline-flex;
  padding: 3px 8px;
  border-radius: 999px;
  background: #f7f8fa;
  color: #6b5a5e;
  font-size: 12px;
  font-weight: 800;
}

.status-pill.completed {
  background: #f6ffed;
  color: #2f7a16;
}

.status-pill.partial {
  background: #fff8e6;
  color: #9a6400;
}

.status-pill.error {
  background: #fff1f0;
  color: #c53333;
}

.actions {
  text-align: right;
}

.actions button {
  margin-left: 8px;
  min-height: 30px;
  padding: 0 10px;
  border: 1px solid #f0d9dd;
  border-radius: 999px;
  background: #fff;
  color: #7b666b;
  cursor: pointer;
}

.actions button:hover {
  border-color: var(--primary);
  color: var(--primary);
}

.empty-panel,
.loading-state {
  display: grid;
  place-items: center;
  min-height: 240px;
  color: #8a6e73;
}

.pagination {
  display: flex;
  justify-content: center;
  gap: 10px;
  padding: 14px;
}

.pagination button {
  min-height: 32px;
  padding: 0 12px;
  border: 1px solid #f0d9dd;
  border-radius: 999px;
  background: #fff;
}

.detail-backdrop {
  position: fixed;
  inset: 0;
  z-index: 800;
  display: flex;
  justify-content: flex-end;
  background: rgba(28, 20, 22, 0.34);
}

.detail-drawer {
  width: min(760px, 100vw);
  height: 100%;
  overflow-y: auto;
  background: #fff;
  box-shadow: -18px 0 44px rgba(29, 18, 20, 0.16);
}

.detail-drawer header {
  position: sticky;
  top: 0;
  z-index: 1;
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 22px 24px;
  border-bottom: 1px solid #f1eeee;
  background: #fff;
}

.detail-drawer h2 {
  margin: 0;
  color: #241d1f;
  font-size: 22px;
}

.detail-drawer header p {
  margin: 8px 0 0;
  color: #8a6e73;
  font-size: 13px;
}

.close-btn {
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 999px;
  background: #f7f8fa;
  color: #6b5a5e;
  font-size: 22px;
  cursor: pointer;
}

.content-block {
  margin: 16px 24px;
  padding: 14px;
  border: 1px solid #f1eeee;
  border-radius: 8px;
  background: #fffdfd;
}

.content-block span {
  display: block;
  margin-bottom: 8px;
  color: var(--primary);
  font-size: 12px;
  font-weight: 900;
}

.content-block p {
  margin: 0;
  color: #33282b;
  line-height: 1.7;
  white-space: pre-wrap;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-list em {
  padding: 5px 9px;
  border-radius: 999px;
  background: #fff0f2;
  color: var(--primary);
  font-size: 12px;
  font-style: normal;
  font-weight: 800;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(132px, 1fr));
  gap: 12px;
  padding: 0 24px 20px;
}

.image-item {
  overflow: hidden;
  border: 1px solid #f1eeee;
  border-radius: 8px;
}

.image-item img,
.image-item div {
  display: grid;
  place-items: center;
  width: 100%;
  aspect-ratio: 3/4;
  background: #f7f8fa;
  color: #9b8a8e;
  object-fit: cover;
}

.image-item span {
  display: block;
  padding: 8px 10px;
  color: #8a6e73;
  font-size: 12px;
  font-weight: 800;
}

.detail-open {
  margin: 0 24px 24px;
}

@media (max-width: 860px) {
  .filter-bar {
    display: grid;
  }

  .summary {
    margin-left: 0;
    text-align: left;
  }

  .works-table {
    table-layout: auto;
  }

  .works-table th:nth-child(4),
  .works-table td:nth-child(4),
  .works-table th:nth-child(6),
  .works-table td:nth-child(6) {
    display: none;
  }
}
</style>
