import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Avatar from './Avatar'
import { api, Member } from '../lib/api'
import { getTelegramUser, hapticImpact } from '../lib/telegram'
import logoHorizontal from '../assets/logo-horizontal.png'
import { HOME_ROUTE } from '../lib/routes'

export default function TopBar() {
  const navigate = useNavigate()
  const [member, setMember] = useState<Member | null>(null)
  const tgUser = getTelegramUser()

  useEffect(() => {
    api.getMe().then(setMember).catch(() => {})
  }, [])

  const photoUrl = member ? (member.intro_image ?? api.photoUrl(member.user_id)) : null
  const displayName = member?.intro_name ?? tgUser?.first_name ?? 'Me'

  function goHome() {
    hapticImpact('light')
    navigate(HOME_ROUTE)
  }

  return (
    <header className="flex-shrink-0 border-b border-border/40 bg-bg/95 backdrop-blur-sm">
      <div className="flex items-center justify-between gap-3 px-4 py-3">
        <button
          type="button"
          onClick={() => {
            hapticImpact('light')
            navigate('/profile')
          }}
          className="flex h-11 w-11 items-center justify-center rounded-full transition-transform active:scale-95"
          aria-label="Open profile"
        >
          <Avatar src={photoUrl} name={displayName} size="sm" ring />
        </button>

        <button
          type="button"
          onClick={goHome}
          className="min-w-0 flex-1 px-1 text-center transition-opacity active:opacity-80"
          aria-label="Go to home"
        >
          <p className="truncate font-display text-[19px] font-light tracking-[0.02em] text-cream sm:text-[22px]">
            Baltic Business Club
          </p>
        </button>

        <button
          type="button"
          onClick={goHome}
          className="flex w-16 flex-shrink-0 justify-end transition-opacity active:opacity-80 sm:w-20"
          aria-label="Go to home"
        >
          <img
            src={logoHorizontal}
            alt="Baltic Business Club"
            className="h-6 w-auto select-none opacity-95 sm:h-7"
          />
        </button>
      </div>
    </header>
  )
}
