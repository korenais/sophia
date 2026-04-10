import { useState, useEffect, useRef } from 'react'
import { api, Member } from '../lib/api'
import MemberCard from '../components/MemberCard'
import LoadingScreen from '../components/LoadingScreen'

export default function PeoplePage() {
  const [members, setMembers] = useState<Member[]>([])
  const [filtered, setFiltered] = useState<Member[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    api.getMembers()
      .then(data => { setMembers(data); setFiltered(data) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    const q = search.toLowerCase().trim()
    if (!q) { setFiltered(members); return }
    setFiltered(members.filter(m =>
      [m.intro_name, m.intro_location, m.field_of_activity, m.intro_skills, m.intro_description]
        .some(f => f?.toLowerCase().includes(q))
    ))
  }, [search, members])

  // Country cloud
  const countries = members.reduce<Record<string, number>>((acc, m) => {
    if (!m.intro_location) return acc
    const country = m.intro_location.split(',').pop()?.trim() ?? m.intro_location
    acc[country] = (acc[country] ?? 0) + 1
    return acc
  }, {})
  const topCountries = Object.entries(countries)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)

  if (loading) return <LoadingScreen />

  return (
    <div className="flex flex-col h-full bg-bg">

      {/* Header */}
      <div className="flex-shrink-0 px-4 pt-4 pb-3">
        <div className="mb-4">
          <h1 className="font-display text-2xl font-light tracking-wide text-cream">
            Резиденты
          </h1>
          <p className="text-muted text-xs font-body mt-0.5">
            {members.length} участников клуба
          </p>
        </div>

        {/* Search */}
        <div className="relative">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
               width="16" height="16" viewBox="0 0 24 24" fill="none">
            <circle cx="11" cy="11" r="7" stroke="#7A8099" strokeWidth="1.5"/>
            <path d="M20 20l-2.5-2.5" stroke="#7A8099" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
          <input
            ref={inputRef}
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Поиск по имени, нише, городу…"
            className="w-full bg-surface border border-border rounded-xl pl-9 pr-4 py-2.5
                       text-[14px] text-cream font-body placeholder:text-muted/60
                       focus:outline-none focus:border-gold/50 transition-colors"
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M1 1l12 12M13 1L1 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Country cloud — only when not searching */}
      {!search && topCountries.length > 0 && (
        <div className="flex-shrink-0 px-4 pb-3">
          <div className="flex flex-wrap gap-1.5">
            {topCountries.map(([country, count]) => (
              <button
                key={country}
                onClick={() => setSearch(country)}
                className="px-2.5 py-1 rounded-lg bg-raised border border-border/60
                           text-[12px] font-body text-muted hover:border-gold/40
                           hover:text-gold/80 transition-colors card-press"
              >
                {country} <span className="text-border">{count}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="gold-divider mx-4 flex-shrink-0" />

      {/* List */}
      <div className="flex-1 scroll-area px-4 pt-3 pb-4">
        {error ? (
          <div className="text-center py-12">
            <p className="text-danger text-sm font-body">{error}</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-16 animate-fade-in">
            <div className="text-gold/20 text-5xl mb-3">◈</div>
            <p className="text-muted text-sm font-body">Ничего не найдено</p>
          </div>
        ) : (
          <div className="flex flex-col gap-2.5">
            {filtered.map((m, i) => (
              <div key={m.user_id} className="animate-fade-up relative"
                   style={{ animationDelay: `${i * 35}ms` }}>
                <MemberCard member={m} index={i} />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
