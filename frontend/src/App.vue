<template>
  <div id="app">
    <header v-if="!isAuthRoute" class="app-header">
      <RouterLink to="/" class="brand-area">
        <div class="brand-mark">薯</div>
        <div class="brand-copy">
          <strong>薯光笔记</strong>
          <small>小红书图文创作台</small>
        </div>
      </RouterLink>

      <nav class="nav-menu">
        <RouterLink to="/" class="nav-item" active-class="active">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
          创作
        </RouterLink>
        <RouterLink to="/ideas" class="nav-item" active-class="active">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v5"></path><path d="M12 17v5"></path><path d="M4.22 4.22l3.54 3.54"></path><path d="M16.24 16.24l3.54 3.54"></path><path d="M2 12h5"></path><path d="M17 12h5"></path><path d="M4.22 19.78l3.54-3.54"></path><path d="M16.24 7.76l3.54-3.54"></path></svg>
          选题
        </RouterLink>
        <RouterLink to="/history" class="nav-item" active-class="active">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line></svg>
          我的创作
        </RouterLink>
        <RouterLink to="/tasks" class="nav-item" active-class="active">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><path d="M12 6v6l4 2"></path></svg>
          任务
        </RouterLink>
        <RouterLink v-if="auth.isAdmin" to="/users" class="nav-item" active-class="active">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M22 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>
          用户
        </RouterLink>
        <RouterLink v-if="auth.isAdmin" to="/works" class="nav-item" active-class="active">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="14" rx="2"></rect><path d="M7 8h5"></path><path d="M7 12h10"></path><path d="M7 16h7"></path></svg>
          作品
        </RouterLink>
        <RouterLink to="/settings" class="nav-item" active-class="active">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"></circle><path d="M12 1v6m0 6v6m-6-6h6m6 0h-6"></path></svg>
          设置
        </RouterLink>
      </nav>

      <div class="header-status">
        <span class="status-dot"></span>
        <span class="user-label">{{ auth.user ? `${auth.user.name} · ${roleText}` : '未登录' }}</span>
        <span v-if="auth.user" class="quota-chip">{{ quotaText }}</span>
        <button v-if="auth.user" class="logout-link" @click="logout">退出</button>
      </div>
    </header>

    <main :class="isAuthRoute ? 'auth-main' : 'layout-main'">
      <RouterView v-slot="{ Component, route }">
        <component :is="Component" />

        <footer v-if="route.path !== '/' && route.path !== '/auth'" class="global-footer">
          <div class="footer-content">
            <div class="footer-tip">在设置页配置文本和图片服务后即可开始生成。</div>
            <div class="footer-text">© 2026 薯光笔记 · 本地创作工具</div>
          </div>
        </footer>
      </RouterView>
    </main>
  </div>
</template>

<script setup lang="ts">
import { RouterView, RouterLink } from 'vue-router'
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { setupAutoSave } from './stores/generator'
import { useAuthStore } from './stores/auth'

const router = useRouter()
const auth = useAuthStore()

const isAuthRoute = computed(() => router.currentRoute.value.path === '/auth')

const roleText = computed(() => {
  if (auth.user?.role === 'admin') return '管理员'
  if (auth.user?.role === 'editor') return '编辑'
  return '成员'
})

const quotaText = computed(() => {
  if (!auth.user) return ''
  if (auth.isAdmin) return '额度不限'
  if (auth.user.quota_limit === null || auth.user.quota_limit === undefined) return '额度不限'
  return `可用 ${auth.user.quota_remaining ?? 0} 张`
})

onMounted(() => {
  setupAutoSave()
})

async function logout() {
  await auth.logout()
  router.push('/auth')
}
</script>
