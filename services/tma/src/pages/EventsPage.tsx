import { useState, useEffect, useMemo, useRef } from 'react'
import { hapticImpact, openLink } from '../lib/telegram'

// ─── Types ────────────────────────────────────────────────────────────────────

interface CalendarEvent {
  id: string
  source: string
  date: string // YYYY-MM-DD
  title: string
  description: string
  start_time: string | null
  end_time: string | null
  start_at: string | null
  end_at: string | null
  members_only: boolean
  working_group: boolean
  tags: string[]
  color: string
  text_color: string
  image: string
  url: string
  recurring: boolean
}

interface FientaData {
  title: string | null
  description: string | null
  start_at: string | null
  end_at: string | null
  location_name: string | null
  location_address: string | null
  latitude: number | null
  longitude: number | null
  price: string | null
  currency: string | null
  image: string | null
}

// ─── Constants ────────────────────────────────────────────────────────────────

const EVENTS_API = 'https://balticbusinessclub.com/wp-json/bbc-calendar/v1/miniapp/events'

const WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

const MONTHS = [
  'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь',
]

// BBC calendar uses dark hex colors; map them to brighter display versions for dots
const DOT_COLOR_MAP: Record<string, string> = {
  '#21426e': '#5b9fd6',
  '#213d5c': '#5b9fd6',
  '#7a2e2e': '#e06060',
  '#144d32': '#3ec47a',
}
function dotColor(apiColor: string): string {
  return DOT_COLOR_MAP[apiColor?.toLowerCase()] ?? apiColor ?? '#C9A84C'
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function toDateKey(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

async function fetchEvents(year: number, month: number): Promise<CalendarEvent[]> {
  const mm = String(month + 1).padStart(2, '0')
  const lastDay = new Date(year, month + 1, 0).getDate()
  const from = `${year}-${mm}-01`
  const to   = `${year}-${mm}-${lastDay}`
  const res  = await fetch(`${EVENTS_API}?from=${from}&to=${to}&limit=1000`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const data = await res.json()
  return (data.events ?? []) as CalendarEvent[]
}

function eventDisplayName(ev: CalendarEvent): string {
  return ev.title?.trim() || ev.description?.trim() || 'Мероприятие'
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function EventsPage() {
  const today    = useMemo(() => new Date(), [])
  const todayKey = useMemo(() => toDateKey(today), [today])

  const [year, setYear]           = useState(today.getFullYear())
  const [month, setMonth]         = useState(today.getMonth())
  const [events, setEvents]       = useState<CalendarEvent[]>([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState<string | null>(null)
  const [selectedDay, setSelectedDay] = useState<string>(todayKey)
  const [detailEvent, setDetailEvent] = useState<CalendarEvent | null>(null)
  // Pre-fetched Fienta data keyed by event URL
  const [fientaCache, setFientaCache] = useState<Record<string, FientaData>>({})

  useEffect(() => {
    setLoading(true)
    setError(null)
    fetchEvents(year, month)
      .then(setEvents)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [year, month])

  const eventsByDay = useMemo(() => {
    const map: Record<string, CalendarEvent[]> = {}
    for (const ev of events) {
      if (!map[ev.date]) map[ev.date] = []
      map[ev.date].push(ev)
    }
    return map
  }, [events])

  const calendarDays = useMemo(() => {
    const firstDay    = new Date(year, month, 1)
    const startOffset = (firstDay.getDay() + 6) % 7
    const daysInMonth = new Date(year, month + 1, 0).getDate()
    const daysInPrev  = new Date(year, month, 0).getDate()

    const cells: Array<{ date: Date; inMonth: boolean }> = []
    for (let i = startOffset - 1; i >= 0; i--)
      cells.push({ date: new Date(year, month - 1, daysInPrev - i), inMonth: false })
    for (let d = 1; d <= daysInMonth; d++)
      cells.push({ date: new Date(year, month, d), inMonth: true })
    const trailing = 42 - cells.length
    for (let d = 1; d <= trailing; d++)
      cells.push({ date: new Date(year, month + 1, d), inMonth: false })
    return cells
  }, [year, month])

  function goMonth(delta: number) {
    hapticImpact('light')
    setMonth(m => {
      const next = m + delta
      if (next < 0)  { setYear(y => y - 1); return 11 }
      if (next > 11) { setYear(y => y + 1); return 0  }
      return next
    })
    setSelectedDay('')
  }

  function selectDay(key: string) {
    hapticImpact('light')
    setSelectedDay(prev => (prev === key ? '' : key))
  }

  const selectedEvents = selectedDay ? (eventsByDay[selectedDay] ?? []) : []

  // Pre-fetch Fienta data for all events in the selected day
  useEffect(() => {
    for (const ev of selectedEvents) {
      if (!ev.url?.includes('fienta.com') || fientaCache[ev.url]) continue
      fetch(`/api/tma/fienta-event?url=${encodeURIComponent(ev.url)}`)
        .then(r => r.ok ? r.json() : null)
        .then(d => d && setFientaCache(prev => ({ ...prev, [ev.url]: d })))
        .catch(() => {})
    }
  }, [selectedDay, selectedEvents.length]) // eslint-disable-line react-hooks/exhaustive-deps

  const selectedLabel  = selectedDay
    ? new Date(selectedDay + 'T00:00:00').toLocaleDateString('ru-RU', {
        weekday: 'long', day: 'numeric', month: 'long',
      })
    : null

  return (
    <div className="flex flex-col h-full bg-bg">

      {/* ── Month navigation ── */}
      <div className="flex-shrink-0 flex items-center justify-between px-4 pt-3 pb-2">
        <button onClick={() => goMonth(-1)}
          className="w-9 h-9 flex items-center justify-center rounded-full
                     bg-raised border border-border/60 active:scale-95 transition-transform"
          aria-label="Предыдущий месяц">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M15 18l-6-6 6-6" stroke="#C9A84C" strokeWidth="1.5"
                  strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>

        <div className="text-center leading-none">
          <h1 className="font-display text-[20px] font-light tracking-wide text-cream">
            {MONTHS[month]}
          </h1>
          <p className="text-muted text-[10px] font-body tracking-[3px]">{year}</p>
        </div>

        <button onClick={() => goMonth(1)}
          className="w-9 h-9 flex items-center justify-center rounded-full
                     bg-raised border border-border/60 active:scale-95 transition-transform"
          aria-label="Следующий месяц">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M9 18l6-6-6-6" stroke="#C9A84C" strokeWidth="1.5"
                  strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>

      {/* ── Weekday headers ── */}
      <div className="flex-shrink-0 grid grid-cols-7 px-2">
        {WEEKDAYS.map(d => (
          <div key={d}
               className="text-center text-[10px] text-muted/50 font-body tracking-wider py-0.5">
            {d}
          </div>
        ))}
      </div>

      {/* ── Calendar grid ── */}
      <div className="flex-shrink-0 grid grid-cols-7 px-2">
        {calendarDays.map(({ date, inMonth }) => {
          const key        = toDateKey(date)
          const dayEvs     = eventsByDay[key] ?? []
          const isToday    = key === todayKey
          const isSelected = key === selectedDay
          const hasEvents  = dayEvs.length > 0

          return (
            <button key={key}
              onClick={() => inMonth && selectDay(key)}
              disabled={!inMonth}
              className={[
                'flex flex-col items-center justify-start py-1 rounded-xl',
                'border transition-all duration-150',
                inMonth ? 'active:scale-95' : 'pointer-events-none opacity-15',
                isSelected
                  ? 'bg-gold/15 border-gold/40'
                  : isToday
                  ? 'bg-raised border-gold/25'
                  : 'border-transparent',
              ].join(' ')}
            >
              <span className={[
                'text-[12px] font-body leading-none',
                isSelected ? 'text-gold font-semibold'
                  : isToday  ? 'text-gold'
                  : inMonth  ? 'text-cream'
                  : 'text-muted',
              ].join(' ')}>
                {date.getDate()}
              </span>
              <div className="flex items-center justify-center gap-[3px] mt-[4px] min-h-[5px]">
                {hasEvents && dayEvs.slice(0, 3).map((ev, i) => (
                  <span key={i}
                    className="w-[4px] h-[4px] rounded-full flex-shrink-0"
                    style={{ backgroundColor: dotColor(ev.color) }}
                  />
                ))}
                {dayEvs.length > 3 && (
                  <span className="text-[7px] text-muted font-body leading-none">
                    +{dayEvs.length - 3}
                  </span>
                )}
              </div>
            </button>
          )
        })}
      </div>

      {/* ── Legend ── */}
      <div className="flex-shrink-0 flex items-center gap-4 px-4 mt-2">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: '#5b9fd6' }} />
          <span className="text-[11px] text-muted font-body">Члены клуба</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: '#e06060' }} />
          <span className="text-[11px] text-muted font-body">Открытое</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: '#3ec47a' }} />
          <span className="text-[11px] text-muted font-body">Спецмероприятие</span>
        </div>
      </div>

      {/* ── Divider ── */}
      <div className="gold-divider mx-4 mt-2 flex-shrink-0" />

      {/* ── Events panel ── */}
      <div className="flex-1 scroll-area px-4 pt-2 pb-4">
        {loading ? (
          <div className="flex items-center justify-center py-10">
            <div className="w-5 h-5 rounded-full border-2 border-gold/30 border-t-gold animate-spin" />
          </div>

        ) : error ? (
          <div className="text-center py-10 animate-fade-in">
            <p className="text-danger text-sm font-body">{error}</p>
            <button
              onClick={() => { setLoading(true); fetchEvents(year, month).then(setEvents).catch(e => setError(e.message)).finally(() => setLoading(false)) }}
              className="mt-3 text-gold text-sm font-body underline underline-offset-2"
            >
              Попробовать снова
            </button>
          </div>

        ) : !selectedDay ? (
          <div className="text-center py-10 animate-fade-in">
            <div className="text-gold/20 text-4xl mb-2">◈</div>
            <p className="text-muted text-sm font-body">Выберите день в календаре</p>
          </div>

        ) : selectedEvents.length === 0 ? (
          <div className="text-center py-10 animate-fade-in">
            <div className="text-border text-3xl mb-2">—</div>
            <p className="text-muted text-sm font-body">Нет событий в этот день</p>
          </div>

        ) : (
          <div className="animate-fade-up">
            {selectedLabel && (
              <div className="flex items-center gap-2 mb-3">
                <span className="text-[10px] text-gold/60 font-body tracking-[2px] uppercase">
                  {selectedLabel}
                </span>
                <div className="flex-1 h-px bg-border/50" />
              </div>
            )}
            <div className="space-y-2">
              {selectedEvents.map((ev, i) => (
                <EventRow
                  key={ev.id}
                  event={ev}
                  index={i}
                  fienta={ev.url ? fientaCache[ev.url] ?? null : null}
                  onOpen={() => { hapticImpact('light'); setDetailEvent(ev) }}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── Event detail modal ── */}
      {detailEvent && (
        <EventDetail
          event={detailEvent}
          prefetchedFienta={detailEvent.url ? fientaCache[detailEvent.url] ?? null : null}
          onClose={() => setDetailEvent(null)}
        />
      )}
    </div>
  )
}

// ─── Compact row in day list ──────────────────────────────────────────────────

function EventRow({ event, index, fienta, onOpen }: {
  event: CalendarEvent
  index: number
  fienta: FientaData | null
  onOpen: () => void
}) {
  const title    = fienta?.title?.trim() || eventDisplayName(event)
  const dotBg    = event.color || '#C9A84C'
  const isFienta = event.url?.includes('fienta.com')
  const thumb    = fienta?.image ?? null

  return (
    <button
      onClick={onOpen}
      className="w-full text-left bg-surface border border-border/60 rounded-xl
                 overflow-hidden active:scale-[0.98] transition-transform animate-fade-up
                 flex items-stretch"
      style={{ animationDelay: `${index * 60}ms` }}
    >
      {/* Accent bar */}
      <div className="w-[3px] flex-shrink-0" style={{ backgroundColor: dotBg }} />

      <div className="flex-1 px-3 py-2.5 min-w-0 flex items-center gap-2">
        {/* Text */}
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap gap-1 mb-0.5">
            {event.members_only && (
              <span className="inline-flex items-center px-1.5 py-0.5 rounded-full
                               bg-gold/10 border border-gold/25
                               text-[9px] text-gold font-body tracking-wide">
                Члены клуба
              </span>
            )}
            {event.working_group && (
              <span className="inline-flex items-center px-1.5 py-0.5 rounded-full
                               bg-raised border border-border/60
                               text-[9px] text-muted font-body">
                Рабочая группа
              </span>
            )}
            {isFienta && !event.members_only && (
              <span className="inline-flex items-center px-1.5 py-0.5 rounded-full
                               bg-raised border border-border/60
                               text-[9px] text-muted font-body">
                Открытое
              </span>
            )}
          </div>

          <p className="text-[13px] text-cream font-body font-medium leading-snug line-clamp-2">
            {title}
          </p>

          {event.start_time && (
            <p className="text-[11px] text-gold/60 font-body mt-0.5">
              {event.start_time}{event.end_time ? ` — ${event.end_time}` : ''}
            </p>
          )}
        </div>

        {/* Thumbnail or chevron */}
        {thumb ? (
          <div className="flex-shrink-0 w-14 h-14 rounded-lg overflow-hidden border border-border/40">
            <img src={thumb} alt={title} className="w-full h-full object-cover" />
          </div>
        ) : (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="flex-shrink-0 text-muted/40">
            <path d="M9 18l6-6-6-6" stroke="currentColor" strokeWidth="1.5"
                  strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        )}
      </div>
    </button>
  )
}

// ─── Full-screen event detail ─────────────────────────────────────────────────

function EventDetail({ event, prefetchedFienta, onClose }: {
  event: CalendarEvent
  prefetchedFienta: FientaData | null
  onClose: () => void
}) {
  const [fienta, setFienta] = useState<FientaData | null>(prefetchedFienta)
  const [fLoading, setFLoading] = useState(false)
  const isFienta = event.url?.includes('fienta.com')

  useEffect(() => {
    if (!isFienta || prefetchedFienta) return
    setFLoading(true)
    fetch(`/api/tma/fienta-event?url=${encodeURIComponent(event.url)}`)
      .then(r => r.ok ? r.json() : null)
      .then(d => d && setFienta(d))
      .catch(() => {})
      .finally(() => setFLoading(false))
  }, [event.url, isFienta, prefetchedFienta])

  const title   = fienta?.title?.trim() || eventDisplayName(event)
  const image   = fienta?.image || event.image || null
  const dotBg   = event.color || '#C9A84C'

  const timeStr = event.start_time ?? (fienta?.start_at ? fienta.start_at.slice(11, 16) : null)
  const endStr  = event.end_time   ?? (fienta?.end_at   ? fienta.end_at.slice(11, 16)   : null)
  const priceStr = fienta?.price
    ? `${fienta.price} ${fienta.currency ?? ''}`.trim()
    : null

  const description = fienta?.description?.trim() || event.description?.trim() || ''

  const dateLabel = new Date(event.date + 'T00:00:00').toLocaleDateString('ru-RU', {
    weekday: 'long', day: 'numeric', month: 'long',
  })

  return (
    <div className="absolute inset-0 z-50 bg-bg flex flex-col animate-fade-in">

      {/* ── Header bar ── */}
      <div className="flex-shrink-0 flex items-center justify-between px-4 pt-4 pb-3">
        <button
          onClick={() => { hapticImpact('light'); onClose() }}
          className="w-9 h-9 flex items-center justify-center rounded-full
                     bg-raised border border-border/60 active:scale-95 transition-transform"
          aria-label="Назад"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M15 18l-6-6 6-6" stroke="#C9A84C" strokeWidth="1.5"
                  strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
        <span className="text-[11px] text-muted/60 font-body tracking-[2px] uppercase">
          Мероприятие
        </span>
        <div className="w-9" />
      </div>

      {/* ── Scrollable content ── */}
      <div className="flex-1 scroll-area">

        {/* Hero image */}
        {image && (
          <div className="mx-4 mb-4 rounded-xl overflow-hidden">
            <img src={image} alt={title} className="w-full object-cover" style={{ maxHeight: '200px' }} />
          </div>
        )}

        {/* Accent + title area */}
        <div className="relative mx-4 mb-4">
          <div
            className="absolute left-0 top-0 bottom-0 w-[3px] rounded-full"
            style={{ backgroundColor: dotBg }}
          />
          <div className="pl-4">
            {/* Badges */}
            <div className="flex flex-wrap gap-1 mb-2">
              {event.members_only && (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full
                                 bg-gold/10 border border-gold/25
                                 text-[10px] text-gold font-body tracking-wide">
                  Члены клуба
                </span>
              )}
              {event.working_group && (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full
                                 bg-raised border border-border/60
                                 text-[10px] text-muted font-body">
                  Рабочая группа
                </span>
              )}
              {isFienta && !event.members_only && (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full
                                 bg-raised border border-border/60
                                 text-[10px] text-muted font-body">
                  Открытое
                </span>
              )}
            </div>

            <h2 className="font-display text-2xl font-light tracking-wide text-cream leading-snug">
              {title}
            </h2>
          </div>
        </div>

        <div className="gold-divider mx-4 mb-4" />

        {/* Details */}
        <div className="px-4 space-y-4">

          {/* Date + Time */}
          <DetailRow icon="clock">
            <span className="text-cream font-body text-[14px] capitalize">{dateLabel}</span>
            {timeStr && (
              <span className="text-muted font-body text-[13px]">
                {timeStr}{endStr ? ` — ${endStr}` : ''}
              </span>
            )}
          </DetailRow>

          {/* Location (Fienta) */}
          {fienta?.location_name && (
            <DetailRow icon="pin">
              <span className="text-cream font-body text-[14px]">{fienta.location_name}</span>
              {fienta.location_address && (
                <span className="text-muted font-body text-[13px]">{fienta.location_address}</span>
              )}
            </DetailRow>
          )}

          {/* Price (Fienta) */}
          {priceStr && (
            <DetailRow icon="price">
              <span className="text-cream font-body text-[14px]">{priceStr}</span>
              {event.members_only && (
                <span className="text-gold/60 font-body text-[12px]">
                  Для резидентов — промокод при регистрации
                </span>
              )}
            </DetailRow>
          )}

          {/* Loading Fienta */}
          {fLoading && (
            <div className="flex items-center gap-2 py-1">
              <div className="w-4 h-4 rounded-full border border-gold/30 border-t-gold animate-spin" />
              <span className="text-muted text-[12px] font-body">Загрузка деталей…</span>
            </div>
          )}

          {/* Description */}
          {description && (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-[10px] text-gold/60 font-body tracking-[2px] uppercase">О мероприятии</span>
                <div className="flex-1 h-px bg-border/50" />
              </div>
              <p className="text-[13px] text-cream/80 font-body leading-relaxed">
                {description}
              </p>
            </div>
          )}
        </div>

        <div className="h-6" />
      </div>

      {/* ── CTA ── */}
      {event.url && (
        <div className="flex-shrink-0 px-4 py-3 bg-bg border-t border-border/40">
          <button
            onClick={() => { hapticImpact('medium'); openLink(event.url) }}
            className="w-full py-3.5 rounded-xl bg-gold text-bg font-body font-semibold
                       text-[15px] tracking-wide flex items-center justify-center gap-2
                       active:scale-95 transition-transform"
          >
            {isFienta ? 'Зарегистрироваться' : 'Подробнее'}
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor"
                    strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
      )}
    </div>
  )
}

// ─── Detail row helper ────────────────────────────────────────────────────────

function DetailRow({ icon, children }: { icon: 'clock' | 'pin' | 'price'; children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3">
      <div className="w-8 h-8 flex-shrink-0 flex items-center justify-center
                      bg-raised border border-border/60 rounded-lg mt-0.5">
        {icon === 'clock' && (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="9" stroke="#C9A84C" strokeWidth="1.5" />
            <path d="M12 7v5l3 3" stroke="#C9A84C" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        )}
        {icon === 'pin' && (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"
                  stroke="#C9A84C" strokeWidth="1.5" />
            <circle cx="12" cy="9" r="2.5" stroke="#C9A84C" strokeWidth="1.5" />
          </svg>
        )}
        {icon === 'price' && (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="9" stroke="#C9A84C" strokeWidth="1.5" />
            <path d="M12 7v1m0 8v1M9.5 9.5a2.5 2.5 0 015 0c0 1.5-1 2-2.5 2.5S9.5 13 9.5 14.5a2.5 2.5 0 005 0"
                  stroke="#C9A84C" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        )}
      </div>
      <div className="flex flex-col gap-0.5">
        {children}
      </div>
    </div>
  )
}
