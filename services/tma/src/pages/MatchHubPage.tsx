import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, Meeting } from '../lib/api'
import Avatar from '../components/Avatar'
import LoadingScreen from '../components/LoadingScreen'
import { hapticImpact } from '../lib/telegram'

export default function MatchHubPage() {
  const navigate = useNavigate()
  const [meeting, setMeeting] = useState<Meeting | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isSearching, setIsSearching] = useState(false)

  useEffect(() => {
    let active = true

    const loadMatch = async () => {
      try {
        const pending = await api.getPendingMatch()
        if (!active) return

        if (pending) {
          navigate(`/match/${pending.id}`, { replace: true })
          return
        }

        setIsSearching(true)
        const found = await api.findMatch()
        if (!active) return
        if (found) {
          navigate(`/match/${found.id}`, { replace: true })
          return
        }
        setMeeting(found)
      } catch (e) {
        if (!active) return
        setError(e instanceof Error ? e.message : 'Match is unavailable right now')
      } finally {
        if (!active) return
        setIsSearching(false)
        setLoading(false)
      }
    }

    void loadMatch()

    return () => {
      active = false
    }
  }, [])

  if (loading) {
    return (
      <LoadingScreen
        title={isSearching ? 'Ищем подходящий мэтч' : 'Проверяем текущий мэтч'}
        subtitle={isSearching
          ? 'Подбираем для тебя наиболее релевантное знакомство среди участников клуба.'
          : 'Сначала проверяем, есть ли для тебя уже активный мэтч.'}
      />
    )
  }

  if (error) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 px-6 text-center">
        <div className="text-gold/20 text-5xl">◈</div>
        <p className="font-display text-2xl text-cream font-light">Мэтч недоступен</p>
        <p className="text-muted text-sm font-body leading-relaxed">{error}</p>
      </div>
    )
  }

  if (!meeting) {
    return (
      <div className="flex h-full flex-col bg-bg animate-fade-in">
        <div className="px-4 pt-5 pb-4">
          <div className="inline-flex items-center gap-2 rounded-full border border-gold/20 bg-gold/10 px-3 py-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-gold" />
            <span className="text-[11px] font-body uppercase tracking-[0.18em] text-gold">
              Match Hub
            </span>
          </div>
          <h1 className="mt-4 font-display text-[34px] font-light leading-none text-cream">
            Мэтч
          </h1>
          <p className="mt-3 text-[15px] leading-relaxed text-muted">
            Нового мэтча пока нет. Как только система подберет релевантное знакомство, ты увидишь его здесь и в push от бота.
          </p>
        </div>

        <div className="gold-divider mx-4 flex-shrink-0" />

        <div className="flex flex-1 items-center justify-center px-4 py-8">
          <div className="w-full max-w-sm rounded-[26px] border border-border/60 bg-surface p-6 text-center">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full border border-gold/20 bg-gold/10">
              <span className="font-display text-3xl text-gold">◈</span>
            </div>
            <p className="font-display text-[28px] text-cream font-light">Подходящий мэтч пока не найден</p>
            <p className="mt-3 text-sm leading-relaxed text-muted">
              Когда в клубе появится подходящее совпадение, оно будет здесь. Полный и конкретный профиль повышает шанс на сильный мэтч.
            </p>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="mt-5 inline-flex items-center justify-center rounded-full border border-gold/30 bg-gold/10 px-4 py-2 text-sm text-gold transition active:scale-[0.98]"
            >
              Попробовать позже
            </button>
          </div>
        </div>
      </div>
    )
  }

  const matched = meeting.matched_user
  const photoUrl = matched.intro_image ?? api.photoUrl(matched.user_id)

  return (
    <div className="flex h-full flex-col bg-bg animate-fade-in">
      <div className="px-4 pt-5 pb-4">
        <div className="inline-flex items-center gap-2 rounded-full border border-gold/20 bg-gold/10 px-3 py-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-gold animate-pulse" />
          <span className="text-[11px] font-body uppercase tracking-[0.18em] text-gold">
            Новый мэтч
          </span>
        </div>
        <h1 className="mt-4 font-display text-[34px] font-light leading-none text-cream">
          Мэтч
        </h1>
        <p className="mt-3 text-[15px] leading-relaxed text-muted">
          Система нашла для тебя новое знакомство. Открой карточку и реши, готов ли ты продолжить общение.
        </p>
      </div>

      <div className="gold-divider mx-4 flex-shrink-0" />

      <div className="scroll-area flex-1 px-4 py-4">
        <button
          type="button"
          onClick={() => {
            hapticImpact('medium')
            navigate(`/match/${meeting.id}`)
          }}
          className="w-full rounded-[28px] border border-gold/20 bg-surface p-5 text-left transition-transform active:scale-[0.99]"
        >
          <div className="mb-4 flex items-start justify-between gap-3">
            <div>
              <p className="text-[11px] font-body uppercase tracking-[0.18em] text-gold/70">
                AI Concierge
              </p>
              <h2 className="mt-2 font-display text-[30px] font-light text-cream">
                {matched.intro_name ?? 'Резидент клуба'}
              </h2>
              {matched.field_of_activity && (
                <p className="mt-2 text-sm leading-relaxed text-gold/90">
                  {matched.field_of_activity}
                </p>
              )}
              {matched.intro_location && (
                <p className="mt-2 text-sm text-muted">{matched.intro_location}</p>
              )}
            </div>
            <span className="pt-1 text-gold/40">→</span>
          </div>

          <div className="flex items-center gap-4 rounded-[22px] border border-border/60 bg-raised/60 p-3">
            <Avatar src={photoUrl} name={matched.intro_name} size="lg" ring />
            <p className="line-clamp-4 text-[14px] leading-relaxed text-cream/80">
              {matched.intro_description ?? 'Открой мэтч, чтобы увидеть профиль и детали знакомства.'}
            </p>
          </div>

          <div className="mt-4 flex items-center justify-between">
            <span className="rounded-full border border-gold/20 bg-gold/10 px-3 py-1 text-[12px] text-gold">
              Meeting #{meeting.id}
            </span>
            <span className="text-sm text-muted">Открыть мэтч</span>
          </div>
        </button>
      </div>
    </div>
  )
}
