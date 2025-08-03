import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from '@/pages/DashboardPage.vue'
import router from './router'
import './index.css'

const app = createApp(App).use(router)

app.use(createPinia())
app.use(router)

app.mount('#app')
