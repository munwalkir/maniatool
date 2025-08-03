import { createRouter, createWebHistory } from 'vue-router'
import App from '@/pages/DashboardPage.vue'
import CallbackPage from '@/pages/CallbackPage.vue'
import LoginPage from '@/pages/LoginPage.vue'
import { isAuthenticated } from '@/auth'

const routes = [
  { path: '/', name: 'Dashboard', component: App, meta: { requiresAuth: true } },
  { path: '/login', name: 'Login', component: LoginPage },
  { path: '/', redirect: '/login' },
  { path: '/callback', name: 'Callback', component: CallbackPage },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: routes,
})

router.beforeEach((to, from, next) => {
  if (to.meta.requiresAuth && !isAuthenticated()) {
    next('/login')
  } else {
    next()
  }
})

export default router
