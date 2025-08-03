import { createRouter, createWebHistory } from 'vue-router'
import CallbackPage from '@/pages/CallbackPage.vue'
import HomePage from '@/App.vue' // or wherever your main page is

const routes = [
  { path: '/', component: HomePage },
  { path: '/callback', component: CallbackPage },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: routes,
})

export default router
