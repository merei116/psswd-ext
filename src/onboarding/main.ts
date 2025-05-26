// src/onboarding/main.ts
import { createApp } from 'vue'
import App from './App.vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import { onboardingRoutes } from './routes'

const router = createRouter({
  history: createWebHashHistory(),
  routes: onboardingRoutes
})

createApp(App)
  .use(router)
  .mount('#app')
