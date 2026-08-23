import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

function getWidth() {
  return typeof window === 'undefined' ? 1024 : window.innerWidth
}

export const useUIStore = defineStore('ui', () => {
  // ── State ──────────────────────────────────────────────────────────────
  const sideNavOpen = ref(false)
  const sideNavCollapsed = ref(false)
  const mobileDrawerOpen = ref(false)
  const headerHeight = ref(56)

  // Reactive window width — updated on resize
  const windowWidth = ref(getWidth())

  // Toasts
  const toasts = ref<Array<{
    id: number
    type: 'success' | 'warning' | 'danger' | 'info'
    title: string
    message?: string
    duration?: number
  }>>([])
  let toastId = 0

  // Modals
  const modals = ref<Array<{
    id: string
    component: any
    props?: any
  }>>([])

  // Loading states
  const globalLoading = ref(false)
  const loadingCount = ref(0)

  // ── Getters ────────────────────────────────────────────────────────────
  const isMobile = computed(() => windowWidth.value < 768)
  const isTablet = computed(() => windowWidth.value >= 768 && windowWidth.value < 1024)
  const isDesktop = computed(() => windowWidth.value >= 1024)

  const sideNavWidth = computed(() => {
    if (sideNavCollapsed.value) return 72
    return 260
  })

  // ── Actions ────────────────────────────────────────────────────────────
  
  // SideNav
  function toggleSideNav() {
    if (isMobile.value) {
      mobileDrawerOpen.value = !mobileDrawerOpen.value
    } else {
      sideNavCollapsed.value = !sideNavCollapsed.value
    }
  }

  function openSideNav() {
    if (isMobile.value) {
      mobileDrawerOpen.value = true
    } else {
      sideNavCollapsed.value = false
    }
  }

  function closeSideNav() {
    if (isMobile.value) {
      mobileDrawerOpen.value = false
    } else {
      sideNavCollapsed.value = true
    }
  }

  function setSideNavCollapsed(collapsed: boolean) {
    sideNavCollapsed.value = collapsed
  }

  // Toasts
  function showToast(
    type: 'success' | 'warning' | 'danger' | 'info',
    title: string,
    message?: string,
    duration = 5000
  ) {
    const id = ++toastId
    toasts.value.push({ id, type, title, message, duration })
    
    if (duration > 0) {
      setTimeout(() => {
        removeToast(id)
      }, duration)
    }
    
    return id
  }

  function removeToast(id: number) {
    const index = toasts.value.findIndex(t => t.id === id)
    if (index >= 0) {
      toasts.value.splice(index, 1)
    }
  }

  function clearToasts() {
    toasts.value = []
  }

  // Convenience methods
  function toastSuccess(title: string, message?: string, duration?: number) {
    return showToast('success', title, message, duration)
  }

  function toastWarning(title: string, message?: string, duration?: number) {
    return showToast('warning', title, message, duration)
  }

  function toastDanger(title: string, message?: string, duration?: number) {
    return showToast('danger', title, message, duration)
  }

  function toastInfo(title: string, message?: string, duration?: number) {
    return showToast('info', title, message, duration)
  }

  // Modals
  function openModal(id: string, component: any, props?: any) {
    modals.value.push({ id, component, props })
  }

  function closeModal(id: string) {
    const index = modals.value.findIndex(m => m.id === id)
    if (index >= 0) {
      modals.value.splice(index, 1)
    }
  }

  function closeAllModals() {
    modals.value = []
  }

  // Global loading
  function startLoading() {
    loadingCount.value++
    globalLoading.value = loadingCount.value > 0
  }

  function stopLoading() {
    loadingCount.value = Math.max(0, loadingCount.value - 1)
    globalLoading.value = loadingCount.value > 0
  }

  // Resize handler — updates reactive windowWidth so isMobile/isTablet/isDesktop re-compute
  function handleResize() {
    windowWidth.value = getWidth()
    if (isMobile.value && !sideNavCollapsed.value) {
      sideNavCollapsed.value = true
    }
  }

  // Register resize listener once at store creation time (store is a singleton)
  if (typeof window !== 'undefined') {
    window.addEventListener('resize', handleResize, { passive: true })
  }

  return {
    // State
    sideNavOpen,
    sideNavCollapsed,
    mobileDrawerOpen,
    headerHeight,
    toasts,
    modals,
    globalLoading,
    
    // Getters
    isMobile,
    isTablet,
    isDesktop,
    sideNavWidth,
    
    // Actions
    toggleSideNav,
    openSideNav,
    closeSideNav,
    setSideNavCollapsed,
    showToast,
    removeToast,
    clearToasts,
    toastSuccess,
    toastWarning,
    toastDanger,
    toastInfo,
    openModal,
    closeModal,
    closeAllModals,
    startLoading,
    stopLoading,
    handleResize,
  }
})