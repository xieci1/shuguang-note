<template>
  <div class="auth-page">
    <div v-if="registerNoticeVisible" class="register-notice-backdrop">
      <div class="register-notice" role="dialog" aria-modal="true">
        <span>注册成功</span>
        <h2>{{ registerNoticeTitle }}</h2>
        <p>{{ registerNoticeText }}</p>
        <button class="btn btn-primary" @click="enterAfterRegister">进入创作台</button>
      </div>
    </div>

    <section class="auth-panel">
      <div>
        <div class="brand-mark large">薯</div>
        <h1>薯光笔记</h1>
        <p>登录后继续管理你的图文、文案和图片。第一个注册用户会自动成为管理员。</p>
      </div>

      <div class="auth-card">
        <div class="auth-tabs">
          <button :class="{ active: mode === 'login' }" @click="mode = 'login'">登录</button>
          <button :class="{ active: mode === 'register' }" @click="mode = 'register'">注册</button>
        </div>

        <div v-if="mode === 'register'" class="field">
          <label>姓名</label>
          <input v-model="name" placeholder="你的名字" />
        </div>
        <div class="field">
          <label>邮箱或用户名</label>
          <input v-model="email" :placeholder="mode === 'login' ? '邮箱或用户名' : 'name@example.com'" />
        </div>
        <div class="field">
          <label>密码</label>
          <input v-model="password" type="password" placeholder="至少 6 位" @keyup.enter="submit" />
        </div>

        <div v-if="auth.error" class="auth-error">{{ auth.error }}</div>

        <button class="btn btn-primary auth-submit" @click="submit" :disabled="auth.loading || !canSubmit">
          {{ auth.loading ? '处理中...' : mode === 'login' ? '登录' : '注册并进入' }}
        </button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const mode = ref<'login' | 'register'>('login')
const name = ref('')
const email = ref('')
const password = ref('')
const registerNoticeVisible = ref(false)
const pendingRedirect = ref('/')

const canSubmit = computed(() => {
  return email.value.trim() && password.value.length >= 6 && (mode.value === 'login' || name.value.trim())
})

const registerNoticeTitle = computed(() => {
  if (auth.isAdmin) return '管理员账号已创建'
  const remaining = auth.user?.quota_remaining ?? auth.user?.quota_limit ?? 6
  return `已获得 ${remaining} 张生成额度`
})

const registerNoticeText = computed(() => {
  if (auth.isAdmin) return '你是第一个注册用户，已自动成为管理员，生成额度不限。'
  return '每生成 1 页图片消耗 1 张额度，额度用完后可联系管理员调整。'
})

async function submit() {
  if (!canSubmit.value) return
  const ok = mode.value === 'login'
    ? await auth.login(email.value.trim(), password.value)
    : await auth.register(name.value.trim(), email.value.trim(), password.value)
  if (!ok) return
  const redirect = typeof router.currentRoute.value.query.redirect === 'string'
    ? router.currentRoute.value.query.redirect
    : '/'
  if (mode.value === 'register') {
    pendingRedirect.value = redirect
    registerNoticeVisible.value = true
  } else {
    router.push(redirect)
  }
}

function enterAfterRegister() {
  registerNoticeVisible.value = false
  router.push(pendingRedirect.value)
}
</script>

<style scoped>
.auth-page {
  position: relative;
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background: #f7f8fa;
}

.register-notice-backdrop {
  position: fixed;
  inset: 0;
  z-index: 20;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(20, 18, 19, 0.38);
}

.register-notice {
  width: min(380px, 100%);
  padding: 26px;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 24px 70px rgba(26, 20, 20, 0.22);
}

.register-notice span {
  color: var(--primary);
  font-size: 13px;
  font-weight: 900;
}

.register-notice h2 {
  margin: 8px 0;
  color: var(--text-main);
  font-size: 24px;
  line-height: 1.25;
}

.register-notice p {
  margin: 0 0 18px;
  color: var(--text-sub);
  line-height: 1.7;
}

.register-notice button {
  width: 100%;
}

.auth-panel {
  width: min(920px, 100%);
  display: grid;
  grid-template-columns: 1fr 420px;
  gap: 32px;
  align-items: center;
}

.brand-mark.large {
  width: 58px;
  height: 58px;
  font-size: 28px;
}

.auth-panel h1 {
  margin: 18px 0 10px;
  color: var(--text-main);
  font-size: 38px;
}

.auth-panel p {
  margin: 0;
  color: var(--text-sub);
  line-height: 1.8;
}

.auth-card {
  display: grid;
  gap: 16px;
  padding: 24px;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 20px 60px rgba(26, 20, 20, 0.1);
}

.auth-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  padding: 4px;
  border-radius: 999px;
  background: #f4f4f5;
}

.auth-tabs button {
  min-height: 38px;
  border: none;
  border-radius: 999px;
  background: transparent;
  color: #666;
  cursor: pointer;
  font-weight: 800;
}

.auth-tabs button.active {
  background: #fff;
  color: var(--primary);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.08);
}

.field {
  display: grid;
  gap: 8px;
}

.field label {
  color: var(--text-main);
  font-size: 14px;
  font-weight: 800;
}

.field input {
  min-height: 44px;
  padding: 0 12px;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  font: inherit;
}

.auth-submit {
  width: 100%;
}

.auth-error {
  padding: 12px;
  border-radius: 10px;
  background: #fff1f0;
  color: #d92d42;
  font-weight: 700;
}

@media (max-width: 780px) {
  .auth-panel {
    grid-template-columns: 1fr;
  }
}
</style>
