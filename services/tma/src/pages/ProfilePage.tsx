import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, Member } from '../lib/api'
import { getTelegramUser, hapticImpact } from '../lib/telegram'
import Avatar from '../components/Avatar'
import LoadingScreen from '../components/LoadingScreen'

export default function ProfilePage() {
  const navigate = useNavigate()
  const [member, setMember] = useState<Member | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const tgUser = getTelegramUser()

  useEffect(() => {
    api.getMe()
      .then(setMember)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingScreen />

  if (error || !member) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 px-6 text-center">
        <div className="text-gold/20 text-5xl">◈</div>
        <p className="font-display text-xl text-cream font-light">Профиль не найден</p>
        <p className="text-muted text-sm font-body">
          Пройдите регистрацию через бота, чтобы получить доступ.
        </p>
      </div>
    )
  }

  const photoUrl = member.intro_image ?? api.photoUrl(member.user_id)

  return (
    <div className="flex flex-col h-full bg-bg animate-fade-in">
      <div className="flex-1 scroll-area">

        {/* Header bar */}
        <div className="flex items-center justify-between px-4 pt-4 pb-2">
          <p className="text-[11px] text-gold/50 font-body tracking-[3px] uppercase">
            Мой профиль
          </p>
          <button
            onClick={() => { hapticImpact('light'); navigate('/profile/edit') }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-raised
                       border border-border text-muted text-[12px] font-body
                       active:scale-95 transition-transform"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
              <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"
                    stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"
                    stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
            Редактировать
          </button>
        </div>

        {/* Avatar + Name */}
        <div className="flex flex-col items-center px-4 pt-4 pb-6">
          <div className="relative">
            <Avatar src={photoUrl} name={member.intro_name ?? tgUser?.first_name} size="xl" ring />
            {/* Gold glow ring */}
            <div className="absolute inset-0 rounded-full"
                 style={{ boxShadow: '0 0 24px rgba(201,168,76,0.15)' }} />
          </div>

          <h1 className="font-display text-[28px] font-light text-cream mt-4 text-center leading-tight">
            {member.intro_name ?? tgUser?.first_name ?? 'Участник'}
          </h1>

          {member.field_of_activity && (
            <p className="text-gold text-sm font-body mt-1 tracking-wide text-center">
              {member.field_of_activity}
            </p>
          )}
          {member.intro_location && (
            <p className="text-muted text-sm font-body mt-0.5 flex items-center gap-1">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none">
                <path d="M12 2C8.686 2 6 4.686 6 8c0 5.25 6 12 6 12s6-6.75 6-12c0-3.314-2.686-6-6-6z"
                      stroke="currentColor" strokeWidth="1.5"/>
                <circle cx="12" cy="8" r="2" stroke="currentColor" strokeWidth="1.5"/>
              </svg>
              {member.intro_location}
            </p>
          )}

          {/* Stats row */}
          <div className="flex items-center gap-6 mt-5">
            <StatPill label="Thanks" value={member.thanks_received} icon="★" />
            <div className="w-px h-6 bg-border" />
            <StatPill label="Встречи" value={member.meetings_completed} icon="☕" />
          </div>
        </div>

        <div className="gold-divider mx-4" />

        {/* Profile sections */}
        <div className="px-4 py-5 space-y-5">

          {/* Business section — tabs */}
          <div>
            <SectionLabel title="Бизнес" />

            {member.intro_description ? (
              <ProfileField label="О себе" value={member.intro_description} />
            ) : (
              <EmptyField label="О себе" onEdit={() => navigate('/profile/edit')} />
            )}

            {member.offer ? (
              <ProfileField label="Чем могу помочь" value={member.offer} />
            ) : (
              <EmptyField label="Чем могу помочь" onEdit={() => navigate('/profile/edit')} />
            )}

            {member.request_text ? (
              <ProfileField label="Что ищу" value={member.request_text} />
            ) : (
              <EmptyField label="Что ищу" onEdit={() => navigate('/profile/edit')} />
            )}
          </div>

          {member.intro_skills && (
            <div>
              <SectionLabel title="Экспертиза" />
              <div className="flex flex-wrap gap-1.5 mt-2">
                {member.intro_skills.split(',').map(s => s.trim()).filter(Boolean).map(skill => (
                  <span key={skill}
                        className="px-2.5 py-1 bg-raised border border-border/70 rounded-lg
                                   text-[12px] text-cream/70 font-body">
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          )}

          {member.intro_linkedin && (
            <div>
              <SectionLabel title="LinkedIn" />
              <p className="text-gold/70 text-sm font-body mt-1.5">{member.intro_linkedin}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function StatPill({ label, value, icon }: { label: string; value: number; icon: string }) {
  return (
    <div className="flex flex-col items-center gap-0.5">
      <span className="font-display text-xl text-gold font-light">
        {icon} {value}
      </span>
      <span className="text-[10px] text-muted font-body tracking-wider uppercase">{label}</span>
    </div>
  )
}

function SectionLabel({ title }: { title: string }) {
  return (
    <div className="flex items-center gap-2 mb-2">
      <span className="text-[10px] text-gold/60 font-body tracking-[2px] uppercase">{title}</span>
      <div className="flex-1 h-px bg-border/40" />
    </div>
  )
}

function ProfileField({ label, value }: { label: string; value: string }) {
  return (
    <div className="py-2.5 border-b border-border/30 last:border-0">
      <p className="text-[11px] text-muted/70 font-body mb-0.5">{label}</p>
      <p className="text-[14px] text-cream/85 font-body leading-relaxed">{value}</p>
    </div>
  )
}

function EmptyField({ label, onEdit }: { label: string; onEdit: () => void }) {
  return (
    <button
      onClick={onEdit}
      className="w-full py-2.5 border-b border-border/30 last:border-0 text-left"
    >
      <p className="text-[11px] text-muted/70 font-body mb-0.5">{label}</p>
      <p className="text-[13px] text-border font-body italic">Нажмите, чтобы добавить →</p>
    </button>
  )
}
