<template>
  <div class="container user-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">用户管理</h1>
        <p class="page-subtitle">管理本地工作台里的成员、角色和状态</p>
      </div>
      <button class="btn refresh-btn" @click="loadUsers" :disabled="loading">
        {{ loading ? '刷新中...' : '刷新' }}
      </button>
    </div>

    <section class="user-panel">
      <div class="user-panel-copy">
        <div>
          <span>成员资料</span>
          <strong>添加一个用户</strong>
        </div>
        <p>成员和编辑默认 6 张生成额度，管理员默认不限。</p>
      </div>
      <div class="user-form">
        <label>
          <span>姓名</span>
          <input v-model="form.name" placeholder="例如：运营同学" />
        </label>
        <label>
          <span>邮箱</span>
          <input v-model="form.email" placeholder="name@example.com" />
        </label>
        <label>
          <span>初始密码</span>
          <input v-model="form.password" type="password" placeholder="至少 6 位" />
        </label>
        <label>
          <span>角色</span>
          <select v-model="form.role">
            <option value="member">成员</option>
            <option value="editor">编辑</option>
            <option value="admin">管理员</option>
          </select>
        </label>
        <label>
          <span>额度</span>
          <input v-model="form.quotaLimit" type="number" min="0" placeholder="默认 6" />
        </label>
        <button class="btn btn-primary create-btn" @click="addUser" :disabled="!canCreate || saving">
          {{ saving ? '添加中...' : '添加用户' }}
        </button>
      </div>
    </section>

    <div v-if="error" class="user-error">{{ error }}</div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
    </div>

    <div v-else-if="users.length === 0" class="empty-state-large">
      <h3>暂无用户</h3>
      <p>添加成员后，可以在这里管理角色和启用状态。</p>
    </div>

    <div v-else class="user-list">
      <div class="user-list-head">
        <span>用户</span>
        <span>可用额度</span>
        <span>权限设置</span>
        <span>操作</span>
      </div>
      <article v-for="user in users" :key="user.id" class="user-row">
        <div class="user-profile">
          <div class="user-avatar">{{ user.name.slice(0, 1) }}</div>
          <div class="user-main">
            <div class="user-title">
              <strong>{{ user.name }}</strong>
              <span :class="['status-pill', user.status]">{{ statusText(user.status) }}</span>
            </div>
            <div class="user-meta">
              <span>{{ user.email }}</span>
              <span>{{ roleText(user.role) }}</span>
              <span>{{ formatDate(user.created_at) }}</span>
            </div>
          </div>
        </div>

        <div class="quota-card">
          <span>可用额度</span>
          <strong>{{ quotaAvailableText(user) }}</strong>
          <em>{{ quotaDetailText(user) }}</em>
        </div>

        <div class="user-controls">
          <label>
            <span>角色</span>
            <select :value="user.role" @change="changeRole(user, $event)">
              <option value="member">成员</option>
              <option value="editor">编辑</option>
              <option value="admin">管理员</option>
            </select>
          </label>
          <label>
            <span>额度</span>
            <input
              class="quota-input"
              type="number"
              min="0"
              :value="user.quota_limit ?? ''"
              placeholder="不限"
              @change="changeQuota(user, $event)"
            />
          </label>
        </div>

        <div class="user-actions">
          <button class="action-btn" @click="resetQuotaUsed(user)" :disabled="saving">
            清零已用
          </button>
          <button class="action-btn" @click="toggleStatus(user)" :disabled="saving">
            {{ user.status === 'active' ? '停用' : '启用' }}
          </button>
          <button class="action-btn danger-btn" @click="removeUser(user)" :disabled="saving">
            删除
          </button>
        </div>
      </article>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  createUser,
  deleteUser,
  getUsers,
  updateUser,
  type UserItem,
  type UserRole,
  type UserStatus
} from '../api'

const users = ref<UserItem[]>([])
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const form = reactive<{ name: string; email: string; password: string; role: UserRole; quotaLimit: string }>({
  name: '',
  email: '',
  password: '',
  role: 'member',
  quotaLimit: ''
})

const canCreate = computed(() => form.name.trim() && form.email.trim() && form.password.length >= 6)

async function loadUsers() {
  loading.value = true
  error.value = ''
  try {
    const result = await getUsers()
    users.value = result.success ? result.users : []
    if (!result.success) error.value = result.error || '加载用户失败'
  } catch (e: any) {
    error.value = e.response?.data?.error || e.message || '加载用户失败'
    users.value = []
  } finally {
    loading.value = false
  }
}

async function addUser() {
  saving.value = true
  error.value = ''
  try {
    const payload: {
      name: string
      email: string
      role: UserRole
      password: string
      quota_limit?: number | null
    } = {
      name: form.name.trim(),
      email: form.email.trim(),
      role: form.role,
      password: form.password
    }
    if (form.quotaLimit !== '') {
      payload.quota_limit = parseQuotaLimit(form.quotaLimit)
    }
    const result = await createUser(payload)
    if (!result.success) {
      error.value = result.error || '添加用户失败'
      return
    }
    form.name = ''
    form.email = ''
    form.password = ''
    form.role = 'member'
    form.quotaLimit = ''
    await loadUsers()
  } catch (e: any) {
    error.value = e.response?.data?.error || e.message || '添加用户失败'
  } finally {
    saving.value = false
  }
}

async function changeRole(user: UserItem, event: Event) {
  const role = (event.target as HTMLSelectElement).value as UserRole
  await saveUser(user.id, { role }, '更新角色失败')
}

async function toggleStatus(user: UserItem) {
  const status: UserStatus = user.status === 'active' ? 'disabled' : 'active'
  await saveUser(user.id, { status }, '更新用户状态失败')
}

async function changeQuota(user: UserItem, event: Event) {
  const value = (event.target as HTMLInputElement).value
  await saveUser(user.id, { quota_limit: parseQuotaLimit(value) }, '更新生成额度失败')
}

async function resetQuotaUsed(user: UserItem) {
  await saveUser(user.id, { quota_used: 0 }, '清零已用额度失败')
}

async function saveUser(
  userId: string,
  data: Partial<Pick<UserItem, 'role' | 'status' | 'quota_limit' | 'quota_used'>>,
  message: string
) {
  saving.value = true
  error.value = ''
  try {
    const result = await updateUser(userId, data)
    if (!result.success || !result.user) {
      error.value = result.error || message
      return
    }
    const index = users.value.findIndex(user => user.id === userId)
    if (index !== -1) users.value[index] = result.user
  } catch (e: any) {
    error.value = e.response?.data?.error || e.message || message
  } finally {
    saving.value = false
  }
}

async function removeUser(user: UserItem) {
  if (!confirm(`确定删除用户「${user.name}」吗？`)) return
  saving.value = true
  error.value = ''
  try {
    const result = await deleteUser(user.id)
    if (!result.success) {
      error.value = result.error || '删除用户失败'
      return
    }
    users.value = users.value.filter(item => item.id !== user.id)
  } catch (e: any) {
    error.value = e.response?.data?.error || e.message || '删除用户失败'
  } finally {
    saving.value = false
  }
}

function roleText(role: UserRole) {
  const labels = {
    admin: '管理员',
    editor: '编辑',
    member: '成员'
  }
  return labels[role]
}

function statusText(status: UserStatus) {
  return status === 'active' ? '启用中' : '已停用'
}

function quotaAvailableText(user: UserItem) {
  if (user.quota_limit === null || user.quota_limit === undefined) {
    return '不限'
  }
  return `${user.quota_remaining ?? 0} 张`
}

function quotaDetailText(user: UserItem) {
  if (user.quota_limit === null || user.quota_limit === undefined) {
    return `已用 ${user.quota_used || 0} 张`
  }
  return `总 ${user.quota_limit} · 已用 ${user.quota_used || 0}`
}

function parseQuotaLimit(value: string): number | null {
  if (value === '') return null
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed >= 0 ? Math.floor(parsed) : null
}

function formatDate(value: string) {
  const d = new Date(value)
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

onMounted(loadUsers)
</script>

<style scoped>
.user-page {
  max-width: 1180px;
}

.refresh-btn {
  min-height: 44px;
  border: 1px solid var(--border-color);
  background: #fff;
  color: #2b2022;
  box-shadow: 0 8px 18px rgba(33, 20, 20, 0.04);
}

.user-panel {
  display: grid;
  gap: 20px;
  padding: 22px;
  border: 1px solid #f1eeee;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 10px 28px rgba(33, 20, 20, 0.04);
}

.user-panel-copy {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-end;
}

.user-panel-copy span {
  display: block;
  color: var(--primary);
  font-size: 13px;
  font-weight: 900;
}

.user-panel-copy strong {
  display: block;
  margin-top: 4px;
  color: var(--text-main);
  font-size: 20px;
}

.user-panel-copy p {
  margin: 0;
  color: #9a8b8e;
  font-size: 13px;
}

.user-form {
  display: grid;
  grid-template-columns: minmax(120px, 1fr) minmax(180px, 1.25fr) minmax(130px, 1fr) 130px 130px auto;
  gap: 12px;
  align-items: end;
}

.user-form label,
.user-controls label {
  display: grid;
  gap: 7px;
  min-width: 0;
}

.user-form label span,
.user-controls label span {
  color: #8a6e73;
  font-size: 12px;
  font-weight: 800;
}

.user-form input,
.user-form select,
.user-controls select,
.quota-input {
  width: 100%;
  min-height: 42px;
  padding: 0 12px;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  background: #fff;
  color: var(--text-main);
  font: inherit;
  font-size: 14px;
}

.user-form input:focus,
.user-form select:focus,
.user-controls select:focus,
.quota-input:focus {
  border-color: rgba(255, 36, 66, 0.45);
  box-shadow: 0 0 0 3px rgba(255, 36, 66, 0.08);
  outline: none;
}

.create-btn {
  min-width: 112px;
  min-height: 42px;
  padding: 0 18px;
  border-radius: 10px;
  font-size: 14px;
  white-space: nowrap;
}

.user-error {
  margin-top: 14px;
  padding: 12px;
  border-radius: 10px;
  background: #fff1f0;
  color: #d92d42;
  font-weight: 700;
}

.user-list {
  display: grid;
  gap: 12px;
  margin-top: 18px;
}

.user-list-head {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) 150px 250px 230px;
  gap: 16px;
  padding: 0 18px;
  color: #a29195;
  font-size: 12px;
  font-weight: 900;
}

.user-row {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) 150px 250px 230px;
  gap: 16px;
  align-items: center;
  padding: 18px;
  border: 1px solid #f1eeee;
  border-radius: 14px;
  background: #fff;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

.user-row:hover {
  border-color: #f3d8dd;
  box-shadow: 0 14px 34px rgba(33, 20, 20, 0.06);
}

.user-profile {
  display: flex;
  gap: 14px;
  align-items: center;
  min-width: 0;
}

.user-avatar {
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: #fff0f2;
  color: var(--primary);
  font-weight: 900;
}

.user-main {
  min-width: 0;
}

.quota-card {
  display: grid;
  gap: 3px;
  padding: 10px 12px;
  border: 1px solid #f1eeee;
  border-radius: 10px;
  background: #fff8f9;
}

.quota-card span,
.quota-card em {
  color: #8a6e73;
  font-size: 12px;
  font-style: normal;
}

.quota-card strong {
  color: var(--primary);
  font-size: 18px;
  line-height: 1.2;
}

.user-title,
.user-meta {
  display: flex;
  gap: 10px;
  align-items: center;
}

.user-title strong {
  min-width: 0;
  overflow: hidden;
  color: var(--text-main);
  font-size: 16px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-meta {
  margin-top: 5px;
  color: #7b666b;
  font-size: 13px;
  flex-wrap: wrap;
}

.user-meta span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-pill {
  flex: 0 0 auto;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
}

.status-pill.active {
  background: #ecfdf3;
  color: #027a48;
}

.status-pill.disabled {
  background: #f4f4f5;
  color: #71717a;
}

.user-controls {
  display: grid;
  grid-template-columns: 1fr 100px;
  gap: 10px;
}

.user-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.action-btn {
  min-height: 40px;
  padding: 0 14px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fff;
  color: #2b2022;
  font: inherit;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.18s ease;
}

.action-btn:hover:not(:disabled) {
  border-color: #cfd4dc;
  background: #f9fafb;
  transform: translateY(-1px);
}

.action-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.danger-btn {
  border: 1px solid rgba(217, 45, 66, 0.16);
  background: #fff1f0;
  color: #d92d42;
}

@media (max-width: 1080px) {
  .user-form {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .create-btn {
    width: 100%;
  }

  .user-list-head {
    display: none;
  }

  .user-row {
    grid-template-columns: 1fr;
    align-items: stretch;
  }

  .quota-card {
    width: 100%;
  }

  .user-actions {
    justify-content: flex-start;
  }
}

@media (max-width: 640px) {
  .user-panel-copy,
  .user-form,
  .user-controls,
  .user-actions {
    display: grid;
    grid-template-columns: 1fr;
  }

  .user-profile {
    align-items: flex-start;
  }

  .user-avatar {
    width: 38px;
    height: 38px;
  }
}
</style>
