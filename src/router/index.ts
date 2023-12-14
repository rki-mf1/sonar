import { createRouter, createWebHistory } from 'vue-router'
import GenomeFilterPage from '@/views/GenomeFilterPage.vue'

const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
        {
            path: '/',
            name: 'home',
            component: GenomeFilterPage
        },

    ]
})

export default router
