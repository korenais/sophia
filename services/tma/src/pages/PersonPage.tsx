import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api, Member } from '../lib/api'
import { showBackButton, hideBackButton, hapticImpact, openTelegramLink, openLink } from '../lib/telegram'
import Avatar from '../components/Avatar'
import LoadingScreen from '../components/LoadingScreen'
import PhotoViewer from '../components/PhotoViewer'

export default function PersonPage() {
  const { userId } = useParams<{ userId: string }>()
  const navigate = useNavigate()
  const [member, setMember] = useState<Member | null>(null)
  const [loading, setLoading] = useState(true)
  const [photoOpen, setPhotoOpen] = useState(false)

  useEffect(() => {
    showBackButton(() => navigate(-1))
    return () => hideBackButton()
  }, [])

  useEffect(() => {
    if (!userId) return
    api.getMember(Number(userId))
      .then(setMember)
      .finally(() => setLoading(false))
  }, [userId])

  if (loading) return <LoadingScreen />
  if (!member) return (
    <div className="flex items-center justify-center h-full">
      <p className="text-muted font-body">Резидент не найден</p>
    </div>
  )

  const photoUrl = member.intro_image ?? api.photoUrl(member.user_id)

  return (
    <div className="flex flex-col h-full bg-bg animate-fade-in">
      <div className="flex-1 scroll-area">

        {/* Hero */}
        <div className="relative">
          {/* Gradient overlay bg */}
          <div className="absolute inset-0 bg-gradient-to-b from-raised/80 to-bg" />
          <div
            className="absolute inset-0 opacity-5"
            style={{
              backgroundImage: `radial-gradient(circle at 60% 40%, #C9A84C 0%, transparent 70%)`,
            }}
          />

          <div className="relative flex flex-col items-center pt-10 pb-6 px-4">
            <button
              type="button"
              onClick={() => photoUrl && setPhotoOpen(true)}
              className="transition-transform active:scale-95"
              aria-label="Open profile photo"
            >
              <Avatar src={photoUrl} name={member.intro_name} size="xl" ring pulse />
            </button>

            <div className="mt-4 text-center">
              <h1 className="font-display text-3xl font-light tracking-wide text-cream">
                {member.intro_name ?? 'Участник'}
              </h1>

              {member.field_of_activity && (
                <p className="text-gold font-body text-sm mt-1 tracking-wide">
                  {member.field_of_activity}
                </p>
              )}

              {member.intro_location && (
                <p className="text-muted font-body text-sm mt-0.5 flex items-center justify-center gap-1">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                    <path d="M12 2C8.686 2 6 4.686 6 8c0 5.25 6 12 6 12s6-6.75 6-12c0-3.314-2.686-6-6-6z"
                          stroke="#7A8099" strokeWidth="1.5"/>
                    <circle cx="12" cy="8" r="2" stroke="#7A8099" strokeWidth="1.5"/>
                  </svg>
                  {member.intro_location}
                </p>
              )}

              {/* Thanks badge */}
              {(member.thanks_received > 0 || member.meetings_completed > 0) && (
                <div className="flex items-center justify-center gap-3 mt-3">
                  {member.thanks_received > 0 && (
                    <div className="flex items-center gap-1 bg-gold/10 border border-gold/20
                                    rounded-full px-3 py-1">
                      <span className="text-gold text-xs">★</span>
                      <span className="text-gold text-xs font-body font-medium">
                        {member.thanks_received} Thanks
                      </span>
                    </div>
                  )}
                  {member.meetings_completed > 0 && (
                    <div className="flex items-center gap-1 bg-raised border border-border
                                    rounded-full px-3 py-1">
                      <span className="text-muted text-xs">☕</span>
                      <span className="text-muted text-xs font-body">
                        {member.meetings_completed} встреч
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="gold-divider mx-4" />

        {/* Info sections */}
        <div className="px-4 py-5 space-y-5">

          {/* Description */}
          {member.intro_description && (
            <Section title="О себе">
              <p className="text-[14px] text-cream/80 font-body leading-relaxed">
                {member.intro_description}
              </p>
            </Section>
          )}

          {/* Offer */}
          {member.offer && (
            <Section title="Чем могу помочь">
              <p className="text-[14px] text-cream/80 font-body leading-relaxed">
                {member.offer}
              </p>
            </Section>
          )}

          {/* Request */}
          {member.request_text && (
            <Section title="Что ищу">
              <p className="text-[14px] text-cream/80 font-body leading-relaxed">
                {member.request_text}
              </p>
            </Section>
          )}

          {/* Skills */}
          {member.intro_skills && (
            <Section title="Экспертиза">
              <div className="flex flex-wrap gap-1.5">
                {member.intro_skills.split(',').map(s => s.trim()).filter(Boolean).map(skill => (
                  <span key={skill}
                        className="px-2.5 py-1 bg-raised border border-border/70 rounded-lg
                                   text-[12px] text-cream/70 font-body">
                    {skill}
                  </span>
                ))}
              </div>
            </Section>
          )}

          {/* Hobbies */}
          {member.intro_hobbies_drivers && (
            <Section title="Интересы и драйверы">
              <p className="text-[13px] text-muted font-body leading-relaxed">
                {member.intro_hobbies_drivers}
              </p>
            </Section>
          )}
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex-shrink-0 px-4 py-3 bg-bg border-t border-border/40 space-y-2.5">
        {member.user_telegram_link && (
          <button
            onClick={() => {
              hapticImpact('medium')
              openTelegramLink(member.user_telegram_link!)
            }}
            className="w-full py-3.5 rounded-xl bg-gold text-bg font-body font-semibold
                       text-[15px] tracking-wide flex items-center justify-center gap-2
                       active:scale-95 transition-transform"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M22 2L11 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              <path d="M22 2L15 22l-4-9-9-4 20-7z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round"/>
            </svg>
            Написать в Telegram
          </button>
        )}

        {member.intro_linkedin && (
          <button
            onClick={() => {
              hapticImpact('light')
              openLink(member.intro_linkedin!.startsWith('http')
                ? member.intro_linkedin!
                : `https://linkedin.com/in/${member.intro_linkedin}`)
            }}
            className="w-full py-3 rounded-xl bg-raised border border-border text-muted
                       font-body text-[14px] flex items-center justify-center gap-2
                       active:scale-95 transition-transform"
          >
            LinkedIn →
          </button>
        )}
      </div>

      <PhotoViewer
        open={photoOpen}
        src={photoUrl}
        alt={member.intro_name}
        title={member.intro_name}
        subtitle={member.field_of_activity}
        location={member.intro_location}
        onClose={() => setPhotoOpen(false)}
      />
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-2.5">
        <span className="text-[10px] text-gold/60 font-body tracking-[2px] uppercase">{title}</span>
        <div className="flex-1 h-px bg-border/50" />
      </div>
      {children}
    </div>
  )
}
