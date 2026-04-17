import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/LoginView.vue'),
    meta: { layout: 'auth', requiresGuest: true },
  },
  {
    path: '/',
    component: () => import('@/layouts/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/dashboard/DashboardView.vue') },

      // Clients
      { path: 'clients', name: 'ClientsList', component: () => import('@/views/clients/ClientsListView.vue') },
      { path: 'clients/new', name: 'ClientCreate', component: () => import('@/views/clients/ClientFormView.vue') },
      { path: 'clients/:id', name: 'ClientDetail', component: () => import('@/views/clients/ClientDetailView.vue') },
      { path: 'clients/:id/edit', name: 'ClientEdit', component: () => import('@/views/clients/ClientFormView.vue') },

      // Cases
      { path: 'cases', name: 'CasesList', component: () => import('@/views/cases/CasesListView.vue') },
      { path: 'cases/new', name: 'CaseCreate', component: () => import('@/views/cases/CaseFormView.vue') },
      { path: 'cases/:id', name: 'CaseDetail', component: () => import('@/views/cases/CaseDetailView.vue') },
      { path: 'cases/:id/edit', name: 'CaseEdit', component: () => import('@/views/cases/CaseFormView.vue') },

      // Tasks & Calendar
      { path: 'tasks', name: 'TasksList', component: () => import('@/views/tasks/TasksListView.vue') },
      { path: 'calendar', name: 'Calendar', component: () => import('@/views/tasks/CalendarView.vue') },

      // Billing
      { path: 'billing/time', name: 'TimeEntries', component: () => import('@/views/billing/TimeEntriesView.vue') },
      { path: 'billing/invoices', name: 'InvoicesList', component: () => import('@/views/billing/InvoicesListView.vue') },
      { path: 'billing/invoices/:id', name: 'InvoiceDetail', component: () => import('@/views/billing/InvoiceDetailView.vue') },

      // Profile & Chat
      { path: 'profile', name: 'Profile', component: () => import('@/views/auth/ProfileView.vue') },
      { path: 'chat', name: 'Chat', component: () => import('@/views/chat/ChatView.vue') },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const auth = useAuthStore()

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return next({ name: 'Login', query: { redirect: to.fullPath } })
  }

  if (to.meta.requiresGuest && auth.isAuthenticated) {
    return next({ name: 'Dashboard' })
  }

  if (to.meta.roles && !to.meta.roles.includes(auth.user?.role)) {
    return next({ name: 'Dashboard' })
  }

  next()
})

export default router
