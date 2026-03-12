import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Landing',
    component: () => import('../views/LandingView.vue'),
  },
  {
    path: '/pricing',
    name: 'Pricing',
    component: () => import('../views/PricingView.vue'),
  },
  {
    path: '/signup',
    name: 'Signup',
    component: () => import('../views/SignupView.vue'),
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/RegisterView.vue'),
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: () => import('../views/ForgotPasswordView.vue'),
  },
  {
    path: '/reset-password',
    name: 'ResetPassword',
    component: () => import('../views/ResetPasswordView.vue'),
  },
  {
    path: '/subscription-expired',
    name: 'SubscriptionExpired',
    component: () => import('../views/SubscriptionExpiredView.vue'),
  },
  {
    path: '/workspace',
    name: 'Workspace',
    component: () => import('../views/WorkspaceView.vue'),
    meta: { requiresAuth: true, requiresPaid: true },
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../views/DashboardView.vue'),
    meta: { requiresAuth: true, requiresPaid: true },
  },
  {
    path: '/analytics',
    name: 'Analytics',
    component: () => import('../views/AnalyticsView.vue'),
    meta: { requiresAuth: true, requiresPaid: true },
  },
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('../views/AdminView.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  {
    path: '/portal/:token',
    name: 'CustomerPortal',
    component: () => import('../views/CustomerPortalView.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (to.hash) return { el: to.hash, behavior: 'smooth' }
    if (savedPosition) return savedPosition
    return { top: 0 }
  },
})

router.beforeEach(async (to, from, next) => {
  const token = localStorage.getItem('token')

  // Public routes — anyone can access
  const publicNames = ['Landing', 'Pricing', 'Signup', 'Login', 'Register', 'ForgotPassword', 'ResetPassword', 'SubscriptionExpired', 'CustomerPortal']
  if (publicNames.includes(to.name)) {
    // Redirect authenticated users away from login/register
    if ((to.name === 'Login' || to.name === 'Register') && token) {
      next('/workspace')
    } else {
      next()
    }
    return
  }

  // Auth required — check token
  if (to.meta.requiresAuth && !token) {
    next('/login')
    return
  }

  // Paid access required — check subscription
  if (to.meta.requiresPaid && token) {
    try {
      const { useSubscriptionStore } = await import('../stores/subscription.js')
      const subStore = useSubscriptionStore()
      const status = await subStore.fetchStatus()
      if (!status || !status.is_active) {
        next('/subscription-expired')
        return
      }
    } catch {
      // If subscription check fails, allow through (graceful degradation)
    }
  }

  // Admin required
  if (to.meta.requiresAdmin && token) {
    try {
      const { useAuthStore } = await import('../stores/auth.js')
      const authStore = useAuthStore()
      if (!authStore.user) {
        await authStore.fetchUser()
      }
      if (!authStore.user?.is_admin) {
        next('/workspace')
        return
      }
    } catch {
      next('/workspace')
      return
    }
  }

  next()
})

export default router
