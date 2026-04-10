import { NavLink, useLocation } from 'react-router-dom'
import { hapticImpact } from '../lib/telegram'

const tabs = [
  {
    to: '/people',
    label: 'Люди',
    icon: (active: boolean) => (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
        <circle cx="9" cy="7" r="3.5" stroke={active ? '#C9A84C' : '#7A8099'} strokeWidth="1.5"/>
        <path d="M2 20c0-3.314 3.134-6 7-6s7 2.686 7 6" stroke={active ? '#C9A84C' : '#7A8099'} strokeWidth="1.5" strokeLinecap="round"/>
        <circle cx="17.5" cy="8" r="2.5" stroke={active ? '#C9A84C' : '#7A8099'} strokeWidth="1.3"/>
        <path d="M22 19c0-2.485-2.015-4.5-4.5-4.5" stroke={active ? '#C9A84C' : '#7A8099'} strokeWidth="1.3" strokeLinecap="round"/>
      </svg>
    ),
  },
  {
    to: '/matches',
    label: 'Мэтч',
    icon: (active: boolean) => (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
        <path d="M12 21s-6.5-4.35-8.8-8.06C1.44 10.1 2.09 6.5 5.1 5.02c2.07-1.01 4.34-.35 5.63 1.33C12.02 4.67 14.29 4.01 16.36 5.02c3.01 1.48 3.66 5.08 1.9 7.92C18.5 16.65 12 21 12 21z"
              stroke={active ? '#C9A84C' : '#7A8099'} strokeWidth="1.5" strokeLinejoin="round"/>
      </svg>
    ),
  },
  {
    to: '/events',
    label: 'Ивенты',
    icon: (active: boolean) => (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
        <rect x="3" y="5" width="18" height="16" rx="2" stroke={active ? '#C9A84C' : '#7A8099'} strokeWidth="1.5"/>
        <path d="M8 3v4M16 3v4M3 10h18" stroke={active ? '#C9A84C' : '#7A8099'} strokeWidth="1.5" strokeLinecap="round"/>
      </svg>
    ),
  },
  {
    to: '/requests',
    label: 'Запросы',
    icon: (active: boolean) => (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
        <circle cx="11" cy="11" r="7" stroke={active ? '#C9A84C' : '#7A8099'} strokeWidth="1.5"/>
        <path d="M20 20l-2-2" stroke={active ? '#C9A84C' : '#7A8099'} strokeWidth="1.5" strokeLinecap="round"/>
      </svg>
    ),
  },
  {
    to: '/services',
    label: 'Сервисы',
    icon: (active: boolean) => (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
        <path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 17l-6.2 4.3 2.4-7.4L2 9.4h7.6L12 2z"
              stroke={active ? '#C9A84C' : '#7A8099'} strokeWidth="1.5" strokeLinejoin="round"/>
      </svg>
    ),
  },
]

export default function BottomNav() {
  const { pathname } = useLocation()

  function isTabActive(path: string) {
    if (path === '/matches') return pathname === '/matches' || pathname.startsWith('/match/')
    return pathname.startsWith(path)
  }

  return (
    <nav className="bg-surface border-t border-border nav-safe flex-shrink-0">
      {/* Gold top line */}
      <div className="h-px bg-gradient-to-r from-transparent via-gold/30 to-transparent" />

      <div className="flex items-stretch">
        {tabs.map(tab => {
          const active = isTabActive(tab.to)
          return (
            <NavLink
              key={tab.to}
              to={tab.to}
              onClick={() => hapticImpact('light')}
              className="flex-1 flex flex-col items-center justify-center pt-2.5 pb-1.5 gap-1 relative"
            >
              {active && (
                <span className="absolute top-0 left-1/2 -translate-x-1/2 w-8 h-0.5 bg-gold rounded-full" />
              )}
              {tab.icon(active)}
              <span
                className="text-[10px] font-body font-medium tracking-wider uppercase"
                style={{ color: active ? '#C9A84C' : '#7A8099' }}
              >
                {tab.label}
              </span>
            </NavLink>
          )
        })}
      </div>
    </nav>
  )
}
