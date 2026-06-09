import { defineStore } from 'pinia'
import {
  getAuthToken,
  getCurrentUser,
  loginUser,
  logoutUser,
  registerUser,
  setAuthToken,
  type UserItem
} from '../api'

function errorMessage(e: any, fallback: string) {
  const data = e?.response?.data
  if (data?.error) return data.error
  if (typeof data === 'string' && data.trim()) return data.trim().slice(0, 120)
  if (e?.response?.status) return `${fallback}，服务返回 ${e.response.status}`
  return e?.message || fallback
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: getAuthToken(),
    user: null as UserItem | null,
    loading: false,
    ready: false,
    error: ''
  }),

  getters: {
    isAuthenticated: (state) => !!state.token && !!state.user,
    isAdmin: (state) => state.user?.role === 'admin'
  },

  actions: {
    async bootstrap() {
      if (!this.token) {
        this.ready = true
        return
      }
      this.loading = true
      try {
        const result = await getCurrentUser()
        if (result.success && result.user) {
          this.user = result.user
        } else {
          this.clearSession()
        }
      } catch {
        this.clearSession()
      } finally {
        this.loading = false
        this.ready = true
      }
    },

    async login(email: string, password: string) {
      this.loading = true
      this.error = ''
      try {
        const result = await loginUser({ email, password })
        if (!result.success || !result.token || !result.user) {
          this.error = result.error || '登录失败'
          return false
        }
        this.setSession(result.token, result.user)
        return true
      } catch (e: any) {
        this.error = errorMessage(e, '登录失败')
        return false
      } finally {
        this.loading = false
      }
    },

    async register(name: string, email: string, password: string) {
      this.loading = true
      this.error = ''
      try {
        const result = await registerUser({ name, email, password })
        if (!result.success || !result.token || !result.user) {
          this.error = result.error || '注册失败'
          return false
        }
        this.setSession(result.token, result.user)
        return true
      } catch (e: any) {
        this.error = errorMessage(e, '注册失败')
        return false
      } finally {
        this.loading = false
      }
    },

    async logout() {
      try {
        await logoutUser()
      } finally {
        this.clearSession()
      }
    },

    async refreshUser() {
      if (!this.token) return false
      try {
        const result = await getCurrentUser()
        if (result.success && result.user) {
          this.user = result.user
          return true
        }
      } catch {
        return false
      }
      return false
    },

    setSession(token: string, user: UserItem) {
      this.token = token
      this.user = user
      setAuthToken(token)
    },

    clearSession() {
      this.token = ''
      this.user = null
      setAuthToken('')
    }
  }
})
