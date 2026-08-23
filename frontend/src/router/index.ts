import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { title: 'Dashboard' },
  },
  {
    path: '/agents',
    name: 'Agents',
    component: () => import('@/views/agents/AgentsView.vue'),
    meta: { title: 'Agents' },
  },
  {
    path: '/agents/:type',
    name: 'AgentDetail',
    component: () => import('@/views/agents/AgentDetailView.vue'),
    meta: { title: 'Agent' },
  },
  {
    path: '/p2p',
    name: 'P2PMarket',
    component: () => import('@/views/P2PView.vue'),
    meta: { title: 'P2P Market' },
  },
  {
    path: '/intel',
    name: 'Intelligence',
    component: () => import('@/views/IntelView.vue'),
    meta: { title: 'Intelligence' },
  },
  {
    path: '/journal',
    name: 'Journal',
    component: () => import('@/views/JournalView.vue'),
    meta: { title: 'Trade Journal' },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: { title: 'Settings' },
  },
  // Legacy redirects
  {
    path: '/bot',
    redirect: '/agents/auto-trend',
  },
  {
    path: '/xrp',
    redirect: '/agents/xrp-swing',
  },
  // Catch-all
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    } else {
      return { top: 0 }
    }
  },
})

router.afterEach((to) => {
  const title = to.meta.title as string | undefined
  document.title = title ? `${title} | CryptoTrada` : 'CryptoTrada'
})

export default router
