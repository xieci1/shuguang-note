import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import IdeasView from '../views/IdeasView.vue'
import OutlineView from '../views/OutlineView.vue'
import GenerateView from '../views/GenerateView.vue'
import ResultView from '../views/ResultView.vue'
import HistoryView from '../views/HistoryView.vue'
import SettingsView from '../views/SettingsView.vue'
import TasksView from '../views/TasksView.vue'
import UsersView from '../views/UsersView.vue'
import WorksView from '../views/WorksView.vue'
import AuthView from '../views/AuthView.vue'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
      meta: { requiresAuth: true }
    },
    {
      path: '/outline',
      name: 'outline',
      component: OutlineView,
      meta: { requiresAuth: true }
    },
    {
      path: '/ideas',
      name: 'ideas',
      component: IdeasView,
      meta: { requiresAuth: true }
    },
    {
      path: '/generate',
      name: 'generate',
      component: GenerateView,
      meta: { requiresAuth: true }
    },
    {
      path: '/result',
      name: 'result',
      component: ResultView,
      meta: { requiresAuth: true }
    },
    {
      path: '/history',
      name: 'history',
      component: HistoryView,
      meta: { requiresAuth: true }
    },
    {
      path: '/tasks',
      name: 'tasks',
      component: TasksView,
      meta: { requiresAuth: true }
    },
    {
      path: '/users',
      name: 'users',
      component: UsersView,
      meta: { requiresAuth: true, requiresAdmin: true }
    },
    {
      path: '/works',
      name: 'works',
      component: WorksView,
      meta: { requiresAuth: true, requiresAdmin: true }
    },
    {
      path: '/publish',
      name: 'publish',
      redirect: '/settings'
    },
    {
      path: '/history/:id',
      name: 'history-detail',
      component: HistoryView,
      meta: { requiresAuth: true }
    },
    {
      path: '/settings',
      name: 'settings',
      component: SettingsView,
      meta: { requiresAuth: true }
    },
    {
      path: '/auth',
      name: 'auth',
      component: AuthView
    }
  ]
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.ready) await auth.bootstrap()
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { path: '/auth', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresAdmin && !auth.isAdmin) {
    return { path: '/' }
  }
  if (to.path === '/auth' && auth.isAuthenticated) {
    return { path: '/' }
  }
})

export default router
