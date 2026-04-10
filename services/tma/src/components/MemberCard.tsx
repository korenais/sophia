import { useNavigate } from 'react-router-dom'
import { hapticImpact } from '../lib/telegram'
import Avatar from './Avatar'
import type { Member } from '../lib/api'
import { api } from '../lib/api'

interface Props {
  member: Member
  index?: number
}

export default function MemberCard({ member, index = 0 }: Props) {
  const navigate = useNavigate()
  const photoUrl = member.intro_image ?? api.photoUrl(member.user_id)

  return (
    <button
      onClick={() => { hapticImpact('light'); navigate(`/people/${member.user_id}`) }}
      className="card-press w-full text-left bg-surface rounded-xl border border-border/60 overflow-hidden
                 hover:border-gold/30 transition-colors"
      style={{ animationDelay: `${index * 40}ms` }}
    >
      <div className="flex items-start gap-3.5 p-4">
        {/* Gold accent line */}
        <div className="absolute left-0 top-3 bottom-3 w-0.5 bg-gradient-to-b from-transparent via-gold/40 to-transparent rounded-full" />

        <Avatar src={photoUrl} name={member.intro_name} size="md" ring />

        <div className="flex-1 min-w-0">
          {/* Name */}
          <div className="flex items-center gap-2">
            <h3 className="font-display text-[17px] font-medium text-cream truncate leading-snug">
              {member.intro_name ?? 'Участник'}
            </h3>
            {member.thanks_received > 0 && (
              <span className="flex-shrink-0 text-[11px] text-gold font-body font-medium">
                ★ {member.thanks_received}
              </span>
            )}
          </div>

          {/* Industry + Location */}
          <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
            {member.field_of_activity && (
              <span className="text-[13px] text-muted font-body">
                {member.field_of_activity}
              </span>
            )}
            {member.field_of_activity && member.intro_location && (
              <span className="text-border text-[11px]">·</span>
            )}
            {member.intro_location && (
              <span className="text-[13px] text-muted font-body">
                {member.intro_location}
              </span>
            )}
          </div>

          {/* Skills preview */}
          {member.intro_skills && (
            <p className="mt-1.5 text-[12px] text-muted/80 font-body line-clamp-1">
              {member.intro_skills}
            </p>
          )}
        </div>

        {/* Arrow */}
        <svg className="flex-shrink-0 mt-1" width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M6 4l4 4-4 4" stroke="#3A3F52" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </div>
    </button>
  )
}
