import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, Member, UpdateProfilePayload } from '../lib/api'
import { showBackButton, hideBackButton, hapticImpact, hapticNotification } from '../lib/telegram'
import LoadingScreen from '../components/LoadingScreen'

const FIELDS: { key: keyof UpdateProfilePayload; label: string; placeholder: string; multiline?: boolean }[] = [
  { key: 'intro_name',          label: 'Имя',                  placeholder: 'Алексей Волков' },
  { key: 'field_of_activity',   label: 'Ниша / Отрасль',        placeholder: 'Финтех · CEO' },
  { key: 'intro_location',      label: 'Город, Страна',         placeholder: 'Таллинн, Эстония' },
  { key: 'intro_description',   label: 'О себе',                placeholder: 'Расскажите о своём опыте и пути', multiline: true },
  { key: 'offer',               label: 'Чем могу помочь',       placeholder: 'Пайплайн платёжных систем, связи в банках…', multiline: true },
  { key: 'request_text',        label: 'Что ищу',               placeholder: 'Выход на инвесторов (Seed)…', multiline: true },
  { key: 'intro_skills',        label: 'Экспертиза (через запятую)', placeholder: 'Финтех, M&A, Банкинг' },
  { key: 'intro_linkedin',      label: 'LinkedIn',              placeholder: 'linkedin.com/in/yourname' },
  { key: 'intro_hobbies_drivers', label: 'Интересы и драйверы', placeholder: 'Горы, стартапы, отец двух детей', multiline: true },
]

export default function EditProfilePage() {
  const navigate = useNavigate()
  const [form, setForm] = useState<UpdateProfilePayload>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    showBackButton(() => navigate('/profile'))
    return () => hideBackButton()
  }, [])

  useEffect(() => {
    api.getMe().then(m => {
      setForm({
        intro_name:          m.intro_name ?? '',
        field_of_activity:   m.field_of_activity ?? '',
        intro_location:      m.intro_location ?? '',
        intro_description:   m.intro_description ?? '',
        offer:               m.offer ?? '',
        request_text:        m.request_text ?? '',
        intro_skills:        m.intro_skills ?? '',
        intro_linkedin:      m.intro_linkedin ?? '',
        intro_hobbies_drivers: m.intro_hobbies_drivers ?? '',
      })
    }).finally(() => setLoading(false))
  }, [])

  async function handleSave() {
    hapticImpact('medium')
    setSaving(true)
    try {
      await api.updateMe(form)
      hapticNotification('success')
      setSaved(true)
      setTimeout(() => navigate('/profile'), 800)
    } catch {
      hapticNotification('error')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <LoadingScreen />

  return (
    <div className="flex flex-col h-full bg-bg animate-scale-in">
      {/* Header */}
      <div className="flex-shrink-0 px-4 pt-4 pb-3 border-b border-border/40">
        <h1 className="font-display text-2xl font-light text-cream">Редактировать</h1>
        <p className="text-muted text-xs font-body mt-0.5">Ваш цифровой паспорт клуба</p>
      </div>

      {/* Form */}
      <div className="flex-1 scroll-area px-4 py-4 space-y-4">
        {FIELDS.map(field => (
          <div key={field.key}>
            <label className="block text-[11px] text-gold/60 font-body tracking-[1.5px] uppercase mb-1.5">
              {field.label}
            </label>
            {field.multiline ? (
              <textarea
                value={(form[field.key] as string) ?? ''}
                onChange={e => setForm(f => ({ ...f, [field.key]: e.target.value }))}
                placeholder={field.placeholder}
                rows={3}
                className="w-full bg-surface border border-border rounded-xl px-3.5 py-2.5
                           text-[14px] text-cream font-body placeholder:text-muted/40
                           focus:outline-none focus:border-gold/50 transition-colors resize-none
                           leading-relaxed"
              />
            ) : (
              <input
                type="text"
                value={(form[field.key] as string) ?? ''}
                onChange={e => setForm(f => ({ ...f, [field.key]: e.target.value }))}
                placeholder={field.placeholder}
                className="w-full bg-surface border border-border rounded-xl px-3.5 py-2.5
                           text-[14px] text-cream font-body placeholder:text-muted/40
                           focus:outline-none focus:border-gold/50 transition-colors"
              />
            )}
          </div>
        ))}

        {/* Bottom padding */}
        <div className="h-4" />
      </div>

      {/* Save button */}
      <div className="flex-shrink-0 px-4 py-3 bg-bg border-t border-border/40">
        <button
          onClick={handleSave}
          disabled={saving || saved}
          className="w-full py-3.5 rounded-xl font-body font-semibold text-[15px]
                     transition-all active:scale-95 flex items-center justify-center gap-2"
          style={{
            background: saved ? '#2A3E2C' : '#C9A84C',
            color: saved ? '#4CAF7A' : '#1A1C24',
            border: saved ? '1px solid #4CAF7A33' : 'none',
          }}
        >
          {saving ? (
            <>
              <span className="inline-block w-4 h-4 border-2 border-bg/40 border-t-bg
                               rounded-full animate-spin" />
              Сохранение…
            </>
          ) : saved ? (
            <>✓ Сохранено</>
          ) : (
            'Сохранить изменения'
          )}
        </button>
      </div>
    </div>
  )
}
