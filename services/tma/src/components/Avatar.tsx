interface AvatarProps {
  src?: string | null
  name?: string | null
  size?: 'sm' | 'md' | 'lg' | 'xl'
  ring?: boolean
  pulse?: boolean
}

const sizes = {
  sm:  'w-10 h-10 text-base',
  md:  'w-14 h-14 text-xl',
  lg:  'w-20 h-20 text-2xl',
  xl:  'w-28 h-28 text-4xl',
}

const ringMap = {
  sm:  'ring-[1.5px]',
  md:  'ring-2',
  lg:  'ring-2',
  xl:  'ring-[3px]',
}

function getInitials(name: string | null | undefined): string {
  if (!name) return '?'
  return name
    .split(' ')
    .slice(0, 2)
    .map(w => w[0])
    .join('')
    .toUpperCase()
}

// Stable color from user name
function getColor(name: string | null | undefined): string {
  if (!name) return '#363B4F'
  let h = 0
  for (let i = 0; i < name.length; i++) h = name.charCodeAt(i) + ((h << 5) - h)
  const colors = ['#3D3520','#1E3033','#2D2040','#1E2D2A','#33201E','#1E2833']
  return colors[Math.abs(h) % colors.length]
}

export default function Avatar({ src, name, size = 'md', ring = false, pulse = false }: AvatarProps) {
  return (
    <div
      className={`
        relative rounded-full overflow-hidden flex items-center justify-center flex-shrink-0
        ${sizes[size]}
        ${ring ? `ring-gold ${ringMap[size]}` : ''}
        ${pulse ? 'animate-[pulse-gold_2s_ease_infinite]' : ''}
      `}
      style={{ background: getColor(name) }}
    >
      {src ? (
        <img
          src={src}
          alt={name ?? ''}
          className="w-full h-full object-cover"
          onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
        />
      ) : (
        <span className="font-display text-gold font-light select-none">
          {getInitials(name)}
        </span>
      )}
    </div>
  )
}
