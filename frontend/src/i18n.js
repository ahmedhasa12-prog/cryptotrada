import { createI18n } from 'vue-i18n'
import en from './locales/en.js'
import ar from './locales/ar.js'

const saved = localStorage.getItem('locale') || 'ar'

export const i18n = createI18n({
  legacy: false,
  locale: saved,
  fallbackLocale: 'en',
  messages: { en, ar },
})

export function setLocale(lang) {
  i18n.global.locale.value = lang
  localStorage.setItem('locale', lang)
  document.documentElement.lang = lang
  document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr'
}

// Apply on first load
document.documentElement.lang = saved
document.documentElement.dir = saved === 'ar' ? 'rtl' : 'ltr'
