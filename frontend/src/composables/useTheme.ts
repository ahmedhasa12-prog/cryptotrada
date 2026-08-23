import { ref, computed, watch, onMounted } from 'vue'

type Theme = 'light' | 'dark'

const THEME_KEY = 'cryptotrada-theme'
const THEME_ATTR = 'data-theme'

// Initialize theme from localStorage or system preference
function getInitialTheme(): Theme {
  if (typeof window === 'undefined') return 'dark'
  
  const saved = localStorage.getItem(THEME_KEY) as Theme | null
  if (saved) return saved
  
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

const theme = ref<Theme>(getInitialTheme())
const systemTheme = ref<Theme>('dark')

// Apply theme to document
function applyTheme(t: Theme) {
  document.documentElement.setAttribute(THEME_ATTR, t)
  localStorage.setItem(THEME_KEY, t)
  theme.value = t
}

// Toggle theme
function toggleTheme() {
  applyTheme(theme.value === 'dark' ? 'light' : 'dark')
}

// Set specific theme
function setTheme(t: Theme) {
  applyTheme(t)
}

// Watch for system theme changes
if (typeof window !== 'undefined') {
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  mediaQuery.addEventListener('change', (e) => {
    systemTheme.value = e.matches ? 'dark' : 'light'
    // Only auto-switch if user hasn't set a preference
    if (!localStorage.getItem(THEME_KEY)) {
      applyTheme(systemTheme.value)
    }
  })
}

// Initialize on mount
onMounted(() => {
  applyTheme(theme.value)
})

export function useTheme() {
  const isDark = computed(() => theme.value === 'dark')
  const isLight = computed(() => theme.value === 'light')
  
  return {
    theme: computed(() => theme.value),
    isDark,
    isLight,
    toggleTheme,
    setTheme,
  }
}

// Also export a simple way to get current theme without reactivity
export function getCurrentTheme(): Theme {
  return theme.value
}