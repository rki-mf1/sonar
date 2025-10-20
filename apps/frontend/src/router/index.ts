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
      path: '/:accession/:datasets/table',
      name: 'Table',
      component: TableView,
      props: true,
    },
    {
      path: '/sample/:id',
      name: 'Sample',
      component: SampleView,
    },
    {
      path: '/:accession/:datasets/plots',
      name: 'Plots',
      component: PlotsView,
      props: true,
    },
    {
      path: '/about',
      name: 'About',
      component: AboutView,
    },
  ],
})

export default router
