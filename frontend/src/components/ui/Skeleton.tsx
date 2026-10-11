export function SkeletonLine({ width = '100%', className = '' }: { width?: string; className?: string }) {
  return <div className={`skeleton h-4 ${className}`} style={{ width }} />
}

// Generic skeleton for a loading list/card area - avoids the layout jump a
// centred spinner causes when real content finally arrives.
export default function SkeletonBlock({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-2.5" aria-hidden="true">
      {Array.from({ length: rows }).map((_, i) => (
        <SkeletonLine key={i} width={i === rows - 1 ? '60%' : '100%'} />
      ))}
    </div>
  )
}
