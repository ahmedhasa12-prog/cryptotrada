import './assets/styles/tokens.css'
import './assets/styles/base.css'
import './assets/styles/shared.css'
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { i18n } from './i18n.js'
import router from './router/index'
import App from './App.vue'

const app = createApp(App)
app.use(createPinia())
app.use(i18n)
app.use(router)
app.mount('#app')
