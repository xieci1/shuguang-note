<template>
  <div class="card">
    <div class="section-header">
      <div>
        <h2 class="section-title">小红书发布账号</h2>
        <p class="section-desc">管理用于一键发布的本机登录账号</p>
      </div>
      <button class="btn btn-small" @click="loadAccounts" :disabled="loading">
        {{ loading ? '刷新中...' : '刷新' }}
      </button>
    </div>

    <section class="publish-panel">
      <div>
        <span>账号登录态</span>
        <strong>独立浏览器档案</strong>
        <p>每个账号使用独立 profile。首次使用先打开登录，之后在“我的创作”里选择作品发布。</p>
      </div>
      <div class="account-create">
        <input v-model="newAccountName" placeholder="账号名称，例如：主账号" />
        <button class="btn btn-primary" @click="addAccount" :disabled="!newAccountName.trim() || loading">
          添加账号
        </button>
      </div>
    </section>

    <div v-if="error" class="publish-error">{{ error }}</div>
    <div v-if="notice" class="publish-notice">{{ notice }}</div>

    <div v-if="loading" class="settings-loading">
      <div class="spinner"></div>
    </div>

    <div v-else-if="accounts.length === 0" class="account-empty">
      暂无发布账号，添加后点击“打开登录”完成小红书登录。
    </div>

    <div v-else class="account-list">
      <article v-for="account in accounts" :key="account.id" class="account-row">
        <div class="account-main">
          <div class="account-title">
            <strong>{{ account.name }}</strong>
            <span>{{ account.platform === 'xhs' ? '小红书' : account.platform }}</span>
            <span v-if="auth.isAdmin">{{ account.user?.name || '未绑定用户' }}</span>
          </div>
          <div class="account-meta">
            <span>{{ account.status }}</span>
            <span>{{ account.last_login_at ? formatDate(account.last_login_at) : '未打开登录' }}</span>
          </div>
          <p>{{ account.profile_dir }}</p>
        </div>
        <div class="account-actions">
          <button class="btn" @click="openLogin(account.id)" :disabled="loading">
            打开登录
          </button>
          <button class="btn danger-btn" @click="deleteAccount(account.id)" :disabled="loading">
            删除
          </button>
        </div>
      </article>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  createPublishAccount,
  deletePublishAccount,
  getPublishAccounts,
  openPublishLogin,
  type PublishAccount
} from '../../api'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const loading = ref(false)
const error = ref('')
const notice = ref('')
const newAccountName = ref('')
const accounts = ref<PublishAccount[]>([])

async function loadAccounts() {
  loading.value = true
  error.value = ''
  try {
    const result = await getPublishAccounts('xhs')
    accounts.value = result.success ? result.accounts : []
    if (!result.success) error.value = result.error || '加载发布账号失败'
  } catch (e: any) {
    error.value = e.response?.data?.error || e.message || '加载发布账号失败'
    accounts.value = []
  } finally {
    loading.value = false
  }
}

async function addAccount() {
  loading.value = true
  error.value = ''
  notice.value = ''
  try {
    const result = await createPublishAccount(newAccountName.value.trim(), 'xhs')
    if (!result.success) {
      error.value = result.error || '添加账号失败'
      return
    }
    newAccountName.value = ''
    await loadAccounts()
  } catch (e: any) {
    error.value = e.response?.data?.error || e.message || '添加账号失败'
  } finally {
    loading.value = false
  }
}

async function openLogin(accountId: string) {
  loading.value = true
  error.value = ''
  notice.value = ''
  try {
    const result = await openPublishLogin(accountId)
    if (!result.success) {
      error.value = result.error || '打开登录失败'
      return
    }
    await loadAccounts()
    notice.value = result.logs || '登录执行器已启动'
  } catch (e: any) {
    error.value = e.response?.data?.error || e.message || '打开登录失败'
  } finally {
    loading.value = false
  }
}

async function deleteAccount(accountId: string) {
  if (!confirm('确定删除这个发布账号吗？本地浏览器档案不会自动删除。')) return
  loading.value = true
  error.value = ''
  notice.value = ''
  try {
    const result = await deletePublishAccount(accountId)
    if (!result.success) {
      error.value = result.error || '删除账号失败'
      return
    }
    await loadAccounts()
  } catch (e: any) {
    error.value = e.message || '删除账号失败'
  } finally {
    loading.value = false
  }
}

function formatDate(value: string) {
  const d = new Date(value)
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

onMounted(loadAccounts)
</script>

<style scoped>
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 4px;
  color: #1a1a1a;
}

.section-desc {
  font-size: 14px;
  color: #666;
  margin: 0;
}

.btn-small {
  padding: 6px 12px;
  font-size: 13px;
}

.publish-panel {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: center;
  padding: 18px;
  border: 1px solid #f1eeee;
  border-radius: 8px;
  background: #fff8f9;
}

.publish-panel span {
  color: var(--primary);
  font-size: 13px;
  font-weight: 900;
}

.publish-panel strong {
  display: block;
  margin-top: 4px;
  color: #241d1f;
  font-size: 17px;
}

.publish-panel p {
  margin: 6px 0 0;
  color: #8a6e73;
  line-height: 1.6;
}

.account-create {
  display: flex;
  gap: 10px;
  min-width: min(390px, 100%);
}

.account-create input {
  flex: 1;
  min-height: 42px;
  padding: 0 12px;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  font: inherit;
}

.publish-error {
  margin-top: 16px;
  padding: 12px;
  border-radius: 10px;
  background: #fff1f0;
  color: #d92d42;
  font-weight: 700;
}

.publish-notice {
  margin-top: 16px;
  padding: 12px;
  border: 1px solid #b7ebc6;
  border-radius: 10px;
  background: #f2fff6;
  color: #1f8f45;
  font-weight: 700;
}

.settings-loading,
.account-empty {
  display: grid;
  place-items: center;
  min-height: 96px;
  color: #8a6e73;
}

.account-list {
  display: grid;
  gap: 14px;
  margin-top: 18px;
}

.account-row {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: center;
  padding: 16px;
  border: 1px solid #f1eeee;
  border-radius: 8px;
  background: #fff;
}

.account-main {
  min-width: 0;
  flex: 1;
}

.account-title,
.account-actions,
.account-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.account-title strong {
  color: #241d1f;
}

.account-title span,
.account-meta span {
  padding: 2px 8px;
  border-radius: 999px;
  background: #fff0f2;
  color: var(--primary);
  font-size: 12px;
  font-weight: 800;
}

.account-meta {
  margin-top: 8px;
}

.account-meta span {
  background: #f7f8fa;
  color: #7b666b;
}

.account-main p {
  margin: 8px 0 0;
  overflow-wrap: anywhere;
  color: #9a8589;
  font-size: 12px;
}

.account-actions .btn {
  border: 1px solid var(--border-color);
}

.danger-btn {
  border-color: #ffd0d0 !important;
  background: #fff5f5;
  color: #d92d42;
}

@media (max-width: 760px) {
  .publish-panel,
  .account-row,
  .account-create {
    display: grid;
  }
}
</style>
