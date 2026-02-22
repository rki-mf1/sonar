import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'
import TableView from '@/views/TableView.vue'
import SampleView from '@/views/SampleView.vue'
import PlotsView from '@/views/PlotsView.vue'
import AboutView from '@/views/AboutView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'Home',
      component: HomeView,
    },
    {
      path: '/table',
      name: 'Table',
      component: TableView,
    },
    {
      path: '/sample/:id',
      name: 'Sample',
      component: SampleView,
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
  ],
})

export default router
