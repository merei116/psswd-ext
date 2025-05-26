import { createRouter, createWebHashHistory } from 'vue-router';
import Step1 from './views/Step1.vue';
import Step2 from './views/Step2.vue';
import Step5 from './views/Step5.vue';

export const onboardingRoutes = [
  { path: '/', component: Step1 },
  { path: '/id', component: Step2 },
  { path: '/done', component: Step5 },
];

// Если тебе нужен сам router объект, то так:
export const router = createRouter({
  history: createWebHashHistory(),
  routes: onboardingRoutes,
});