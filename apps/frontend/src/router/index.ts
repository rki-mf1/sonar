import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'
import PlotsView from '@/views/PlotsView.vue'
import AboutView from '@/views/AboutView.vue'
import SampleView from '@/views/SampleView.vue'
import LandingView from '@/views/LandingView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'Landing',
      component: LandingView,
    },
    {
      path: '/home',
      name: 'Home',
      component: HomeView,
    },
    {
      path: '/plots',
      name: 'Plots',
      component: PlotsView,
    },
    {
      path: '/about',
      name: 'About',
      component: AboutView,
    },
    {
      path: '/sample/:id',
      name: 'Sample',
      component: SampleView,
    },
  ],
})

export default router
