import WebApp from '@twa-dev/sdk'

export function initTelegram() {
  WebApp.ready()
  WebApp.expand()
  WebApp.setHeaderColor('#1A1C24')
  WebApp.setBackgroundColor('#1A1C24')
}

export function getTelegramUser() {
  return WebApp.initDataUnsafe.user ?? null
}

export function getInitData(): string {
  return WebApp.initData
}

export function getStartParam(): string | undefined {
  return WebApp.initDataUnsafe.start_param
}

export function hapticImpact(style: 'light' | 'medium' | 'heavy' = 'light') {
  WebApp.HapticFeedback.impactOccurred(style)
}

export function hapticNotification(type: 'success' | 'error' | 'warning') {
  WebApp.HapticFeedback.notificationOccurred(type)
}

export function showBackButton(onClick: () => void) {
  WebApp.BackButton.show()
  WebApp.BackButton.onClick(onClick)
}

export function hideBackButton() {
  WebApp.BackButton.hide()
  WebApp.BackButton.offClick(() => {})
}

export function openTelegramLink(url: string) {
  WebApp.openTelegramLink(url)
}

export function openLink(url: string) {
  WebApp.openLink(url)
}

export function close() {
  WebApp.close()
}

export const tg = WebApp
