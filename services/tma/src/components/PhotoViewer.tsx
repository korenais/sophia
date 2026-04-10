import { useEffect } from 'react'

interface PhotoViewerProps {
  open: boolean
  src?: string | null
  alt?: string | null
  title?: string | null
  subtitle?: string | null
  location?: string | null
  onClose: () => void
}

export default function PhotoViewer({
  open,
  src,
  alt,
  title,
  subtitle,
  location,
  onClose,
}: PhotoViewerProps) {
  useEffect(() => {
    if (!open) return

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }

    document.body.style.overflow = 'hidden'
    window.addEventListener('keydown', handleKeyDown)

    return () => {
      document.body.style.overflow = ''
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [open, onClose])

  if (!open || !src) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center px-4 py-8 animate-fade-in"
      onClick={onClose}
    >
      <div className="absolute inset-0 bg-bg/95 backdrop-blur-sm" />
      <div
        className="absolute inset-0 opacity-20"
        style={{
          backgroundImage: 'radial-gradient(circle at 50% 25%, rgba(201,168,76,0.28) 0%, transparent 45%)',
        }}
      />

      <button
        onClick={onClose}
        className="absolute right-4 top-4 z-10 flex h-10 w-10 items-center justify-center rounded-full
                   border border-gold/20 bg-raised/90 text-gold transition-transform active:scale-95"
        aria-label="Close photo"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        </svg>
      </button>

      <div
        className="relative z-10 w-full max-w-sm overflow-hidden rounded-[28px] border border-gold/25
                   bg-surface/80 px-2 pb-4 pt-5 shadow-[0_0_50px_rgba(201,168,76,0.12)] animate-scale-in"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="absolute inset-x-8 top-0 h-px bg-gradient-to-r from-transparent via-gold/70 to-transparent" />
        {title && (
          <div className="px-4 pb-4 text-center">
            <h2 className="font-display text-[36px] leading-none text-cream">
              {title}
            </h2>
          </div>
        )}
        <div className="relative overflow-hidden rounded-[22px] bg-bg">
          <img
            src={src}
            alt={alt ?? ''}
            className="max-h-[78vh] w-full object-contain"
          />
        </div>
        {(subtitle || location) && (
          <div className="px-4 pt-4 text-center">
            {subtitle && (
              <p className="font-body text-[14px] leading-relaxed text-gold/95">
                {subtitle}
              </p>
            )}
            {location && (
              <div className="mt-2 flex items-center justify-center gap-1.5 text-muted">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M12 2C8.686 2 6 4.686 6 8c0 5.25 6 12 6 12s6-6.75 6-12c0-3.314-2.686-6-6-6z"
                    stroke="currentColor"
                    strokeWidth="1.5"
                  />
                  <circle cx="12" cy="8" r="2" stroke="currentColor" strokeWidth="1.5" />
                </svg>
                <span className="font-body text-[14px]">{location}</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
