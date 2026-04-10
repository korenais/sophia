interface PreviewCard {
  eyebrow: string
  title: string
  text: string
}

interface SkeletonFeaturePageProps {
  phase: string
  title: string
  description: string
  accent: string
  previews: PreviewCard[]
}

export default function SkeletonFeaturePage({
  phase,
  title,
  description,
  accent,
  previews,
}: SkeletonFeaturePageProps) {
  return (
    <div className="flex h-full flex-col bg-bg animate-fade-in">
      <div className="flex-shrink-0 px-4 pt-5 pb-4">
        <div
          className="inline-flex items-center gap-2 rounded-full border px-3 py-1.5"
          style={{ borderColor: `${accent}33`, background: `${accent}12` }}
        >
          <span className="h-1.5 w-1.5 rounded-full" style={{ background: accent }} />
          <span className="text-[11px] font-body uppercase tracking-[0.18em]" style={{ color: accent }}>
            {phase}
          </span>
        </div>

        <h1 className="mt-4 font-display text-[34px] font-light leading-none text-cream">
          {title}
        </h1>
        <p className="mt-3 max-w-[28rem] text-[15px] leading-relaxed text-muted">
          {description}
        </p>
      </div>

      <div className="gold-divider mx-4 flex-shrink-0" />

      <div className="scroll-area flex-1 px-4 py-4">
        <div className="space-y-3">
          {previews.map((preview, index) => (
            <div
              key={preview.title}
              className="animate-fade-up rounded-[22px] border border-border/60 bg-surface/90 p-4"
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <div className="mb-3 flex items-center justify-between gap-4">
                <span className="text-[10px] font-body uppercase tracking-[0.18em]" style={{ color: accent }}>
                  {preview.eyebrow}
                </span>
                <span className="rounded-full border border-border/60 bg-raised px-2.5 py-1 text-[11px] text-muted">
                  Soon
                </span>
              </div>

              <p className="font-display text-[24px] font-light text-cream">
                {preview.title}
              </p>
              <p className="mt-2 text-[14px] leading-relaxed text-muted">
                {preview.text}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
