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
    to: '/profile',
    label: 'Я',
    icon: (active: boolean) => (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="8" r="3.5" stroke={active ? '#C9A84C' : '#7A8099'} strokeWidth="1.5"/>
        <path d="M4 20c0-3.314 3.582-6 8-6s8 2.686 8 6" stroke={active ? '#C9A84C' : '#7A8099'} strokeWidth="1.5" strokeLinecap="round"/>
      </svg>
    ),
  },
]

// Inactive future tabs
const futureTabs = [
  { label: 'Ивенты', icon: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <rect x="3" y="5" width="18" height="16" rx="2" stroke="#3A3F52" strokeWidth="1.5"/>
      <path d="M8 3v4M16 3v4M3 10h18" stroke="#3A3F52" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  )},
  { label: 'Запросы', icon: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <circle cx="11" cy="11" r="7" stroke="#3A3F52" strokeWidth="1.5"/>
      <path d="M20 20l-2-2" stroke="#3A3F52" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  )},
  { label: 'Сервисы', icon: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 17l-6.2 4.3 2.4-7.4L2 9.4h7.6L12 2z" stroke="#3A3F52" strokeWidth="1.5" strokeLinejoin="round"/>
    </svg>
  )},
]

export default function BottomNav() {
  const { pathname } = useLocation()

  return (
    <nav className="bg-surface border-t border-border nav-safe flex-shrink-0">
      {/* Gold top line */}
      <div className="h-px bg-gradient-to-r from-transparent via-gold/30 to-transparent" />

      <div className="flex items-stretch">
        {/* Active tabs */}
        {tabs.map(tab => {
          const active = pathname.startsWith(tab.to)
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

        {/* Future tabs — dimmed */}
        {futureTabs.map(tab => (
          <button
            key={tab.label}
            disabled
            className="flex-1 flex flex-col items-center justify-center pt-2.5 pb-1.5 gap-1 opacity-30 cursor-not-allowed"
          >
            {tab.icon}
            <span className="text-[10px] font-body font-medium tracking-wider uppercase text-border">
              {tab.label}
            </span>
          </button>
        ))}
      </div>
    </nav>
  )
}
