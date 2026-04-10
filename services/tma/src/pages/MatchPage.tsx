import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api, Meeting } from '../lib/api'
import { hapticImpact, hapticNotification, openTelegramLink } from '../lib/telegram'
import Avatar from '../components/Avatar'
import LoadingScreen from '../components/LoadingScreen'
import PhotoViewer from '../components/PhotoViewer'

type Action = 'confirm' | 'decline' | 'already_know'

export default function MatchPage() {
  const { meetingId } = useParams<{ meetingId: string }>()
  const navigate = useNavigate()
  const [meeting, setMeeting] = useState<Meeting | null>(null)
  const [loading, setLoading] = useState(true)
  const [acting, setActing] = useState<Action | null>(null)
  const [done, setDone] = useState<Action | null>(null)
  const [photoOpen, setPhotoOpen] = useState(false)

  useEffect(() => {
    if (!meetingId) return
    api.getMeeting(Number(meetingId))
      .then(setMeeting)
      .finally(() => setLoading(false))
  }, [meetingId])

  async function act(action: Action) {
    if (!meeting || acting) return
    hapticImpact('medium')
    setActing(action)
    try {
      if (action === 'confirm')     await api.confirmMeeting(meeting.id)
      if (action === 'decline')     await api.declineMeeting(meeting.id)
      if (action === 'already_know') await api.alreadyKnow(meeting.id)
      hapticNotification('success')
      setDone(action)
    } catch {
      hapticNotification('error')
      setActing(null)
    }
  }

  if (loading) return <LoadingScreen />

  if (!meeting) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 px-6 text-center">
        <div className="text-gold/20 text-5xl">◈</div>
        <p className="font-display text-xl text-cream font-light">Матч не найден</p>
        <button onClick={() => navigate('/people')}
                className="text-gold text-sm font-body mt-2">
          К резидентам →
        </button>
      </div>
    )
  }

  const matched = meeting.matched_user
  const photoUrl = matched.intro_image ?? api.photoUrl(matched.user_id)

  if (done) {
    return <DoneScreen action={done} member={matched} onClose={() => navigate('/people')} />
  }

  return (
    <div className="flex flex-col h-full bg-bg animate-fade-in">

      {/* Gold glow backdrop */}
      <div className="absolute inset-0 pointer-events-none"
           style={{
             background: 'radial-gradient(ellipse 60% 40% at 50% 20%, rgba(201,168,76,0.06) 0%, transparent 70%)',
           }} />

      {/* Header */}
      <div className="flex-shrink-0 px-4 pt-5 pb-2 text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full
                        bg-gold/10 border border-gold/20 mb-3">
          <span className="w-1.5 h-1.5 rounded-full bg-gold animate-pulse" />
          <span className="text-gold text-[11px] font-body tracking-wider uppercase">
            AI-Консьерж · Новый матч
          </span>
        </div>
        <h1 className="font-display text-[26px] font-light text-cream leading-snug">
          Познакомьтесь с<br />вашим матчем
        </h1>
      </div>

      {/* Profile card */}
      <div className="flex-1 scroll-area px-4 py-4">
        {/* Avatar hero */}
        <div className="flex flex-col items-center mb-6">
          <div className="relative">
            <button
              type="button"
              onClick={() => photoUrl && setPhotoOpen(true)}
              className="transition-transform active:scale-95"
              aria-label="Open match photo"
            >
              <Avatar src={photoUrl} name={matched.intro_name} size="xl" ring pulse />
            </button>
            {/* Decorative rings */}
            <div className="absolute -inset-3 rounded-full border border-gold/10 pointer-events-none" />
            <div className="absolute -inset-6 rounded-full border border-gold/05 pointer-events-none" />
          </div>

          <h2 className="font-display text-2xl font-light text-cream mt-4">
            {matched.intro_name ?? 'Участник'}
          </h2>
          {matched.field_of_activity && (
            <p className="text-gold text-sm font-body mt-0.5">{matched.field_of_activity}</p>
          )}
          {matched.intro_location && (
            <p className="text-muted text-sm font-body mt-0.5">{matched.intro_location}</p>
          )}
          {matched.thanks_received > 0 && (
            <div className="mt-2 px-3 py-1 bg-gold/10 border border-gold/20 rounded-full">
              <span className="text-gold text-xs font-body">★ {matched.thanks_received} Thanks</span>
            </div>
          )}
        </div>

        {/* Info */}
        <div className="space-y-4">
          {matched.intro_description && (
            <MatchInfoBlock title="О себе" text={matched.intro_description} />
          )}
          {matched.offer && (
            <MatchInfoBlock title="Чем может помочь" text={matched.offer} />
          )}
          {matched.request_text && (
            <MatchInfoBlock title="Ищет" text={matched.request_text} />
          )}
          {matched.intro_skills && (
            <div>
              <p className="text-[10px] text-gold/60 font-body tracking-[2px] uppercase mb-2">
                Экспертиза
              </p>
              <div className="flex flex-wrap gap-1.5">
                {matched.intro_skills.split(',').map(s => s.trim()).filter(Boolean).map(skill => (
                  <span key={skill}
                        className="px-2.5 py-1 bg-raised border border-border/60 rounded-lg
                                   text-[12px] text-cream/70 font-body">
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex-shrink-0 px-4 py-3 space-y-2.5 border-t border-border/40 bg-bg">

        {/* Primary: Write */}
        {matched.user_telegram_link && (
          <button
            onClick={() => {
              hapticImpact('medium')
              openTelegramLink(matched.user_telegram_link!)
            }}
            className="w-full py-3.5 rounded-xl bg-gold text-bg font-body font-semibold
                       text-[15px] flex items-center justify-center gap-2
                       active:scale-95 transition-transform"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M22 2L11 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              <path d="M22 2L15 22l-4-9-9-4 20-7z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round"/>
            </svg>
            Написать в Telegram
          </button>
        )}

        {/* Secondary row */}
        <div className="flex gap-2">
          <button
            onClick={() => act('confirm')}
            disabled={!!acting}
            className="flex-1 py-3 rounded-xl bg-raised border border-success/30 text-success
                       font-body text-[13px] font-medium flex items-center justify-center gap-1.5
                       active:scale-95 transition-all"
          >
            {acting === 'confirm' ? <Spinner /> : '✓'} Встретились
          </button>
          <button
            onClick={() => act('already_know')}
            disabled={!!acting}
            className="flex-1 py-3 rounded-xl bg-raised border border-border text-muted
                       font-body text-[13px] font-medium flex items-center justify-center gap-1.5
                       active:scale-95 transition-all"
          >
            {acting === 'already_know' ? <Spinner /> : '~'} Уже знакомы
          </button>
          <button
            onClick={() => act('decline')}
            disabled={!!acting}
            className="flex-1 py-3 rounded-xl bg-raised border border-danger/20 text-danger/70
                       font-body text-[13px] flex items-center justify-center gap-1.5
                       active:scale-95 transition-all"
          >
            {acting === 'decline' ? <Spinner /> : '✕'} Пропустить
          </button>
        </div>
      </div>

      <PhotoViewer
        open={photoOpen}
        src={photoUrl}
        alt={matched.intro_name}
        title={matched.intro_name}
        subtitle={matched.field_of_activity}
        location={matched.intro_location}
        onClose={() => setPhotoOpen(false)}
      />
    </div>
  )
}

function MatchInfoBlock({ title, text }: { title: string; text: string }) {
  return (
    <div className="bg-raised rounded-xl border border-border/60 p-3.5">
      <p className="text-[10px] text-gold/60 font-body tracking-[2px] uppercase mb-1.5">{title}</p>
      <p className="text-[13px] text-cream/80 font-body leading-relaxed">{text}</p>
    </div>
  )
}

function Spinner() {
  return (
    <span className="inline-block w-3.5 h-3.5 border-2 border-current/30 border-t-current
                     rounded-full animate-spin" />
  )
}

function DoneScreen({ action, member, onClose }: {
  action: Action
  member: { intro_name: string | null }
  onClose: () => void
}) {
  const messages = {
    confirm: { icon: '☕', title: 'Отлично!', sub: `Встреча с ${member.intro_name ?? 'резидентом'} подтверждена` },
    decline: { icon: '→',  title: 'Понятно',  sub: 'Мы подберём другой матч в следующий раз' },
    already_know: { icon: '✓', title: 'Учтём', sub: `${member.intro_name ?? 'Резидент'} отмечен как знакомый` },
  }
  const msg = messages[action]

  return (
    <div className="flex flex-col items-center justify-center h-full gap-5 px-6 text-center animate-scale-in">
      <div className="text-5xl">{msg.icon}</div>
      <div>
        <p className="font-display text-2xl text-cream font-light">{msg.title}</p>
        <p className="text-muted text-sm font-body mt-1.5 leading-relaxed">{msg.sub}</p>
      </div>
      <button
        onClick={onClose}
        className="mt-2 px-6 py-3 rounded-xl bg-raised border border-border
                   text-cream font-body text-sm active:scale-95 transition-transform"
      >
        К резидентам
      </button>
    </div>
  )
}
