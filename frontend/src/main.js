import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPersistedState from 'pinia-plugin-persistedstate'
import App from './App.vue'
import router from './router/index'
import vuetify from './plugins/vuetify'
import { useAuthStore } from './stores/auth'

const app = createApp(App)

const pinia = createPinia()
pinia.use(piniaPersistedState)

app.use(pinia)
app.use(router)
app.use(vuetify)

// Listen for forced logout events from axios interceptor
window.addEventListener('auth:logout', () => {
  const auth = useAuthStore()
  auth.logout()
  router.push({ name: 'Login' })
})

app.mount('#app')
