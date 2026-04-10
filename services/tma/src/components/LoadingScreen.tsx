export default function LoadingScreen() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-6 bg-bg animate-fade-in">
      {/* Shield ornament */}
      <div className="relative">
        <svg width="56" height="56" viewBox="0 0 56 56" fill="none">
          <path
            d="M28 4L8 12v16c0 11.046 8.954 22 20 24 11.046-2 20-12.954 20-24V12L28 4z"
            stroke="#C9A84C"
            strokeWidth="1.5"
            fill="none"
            opacity="0.4"
          />
          <path
            d="M28 4L8 12v16c0 11.046 8.954 22 20 24 11.046-2 20-12.954 20-24V12L28 4z"
            stroke="#C9A84C"
            strokeWidth="1.5"
            fill="none"
            strokeDasharray="120"
            strokeDashoffset="120"
            style={{
              animation: 'draw-shield 1.2s ease forwards',
            }}
          />
        </svg>
        <style>{`
          @keyframes draw-shield {
            to { stroke-dashoffset: 0; }
          }
        `}</style>
      </div>

      <div className="text-center">
        <p className="font-display text-xl text-gold font-light tracking-widest uppercase">
          Baltic Business Club
        </p>
        <p className="text-muted text-xs font-body tracking-wider mt-1">загрузка...</p>
      </div>
    </div>
  )
}
