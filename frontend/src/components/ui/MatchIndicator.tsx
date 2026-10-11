// Presents the real, already-computed Job Match score/band - never invents
// or re-derives a number client-side. Band text leads (it's the honest,
// explainable signal); the percentage is secondary, and never presented as
// a guarantee of anything (see CareerKit's "never invent a verdict"
// principle - this is a UI-level expression of the same rule).
const SCORE_STYLE = (score: number) =>
  score >= 80 ? 'badge-success' : score >= 60 ? 'badge-warning' : 'badge-danger'

export function MatchChip({ score, band, className = '' }: { score: number; band?: string | null; className?: string }) {
  return (
    <span title={band ? `Job Match: ${band}` : 'Job Match'} className={`${SCORE_STYLE(score)} ${className}`}>
      {score}% match
    </span>
  )
}

export function MatchSummary({ score, band }: { score: number; band: string }) {
  const style =
    score >= 80 ? { dot: 'bg-green-500', text: 'text-green-700' }
    : score >= 60 ? { dot: 'bg-amber-500', text: 'text-amber-700' }
    : { dot: 'bg-red-500', text: 'text-red-700' }
  return (
    <div className="flex items-center gap-2">
      <span className={`w-2 h-2 rounded-full ${style.dot}`} />
      <span className={`text-sm font-semibold ${style.text}`}>{band}</span>
      <span className="text-caption">· {score}% estimated match</span>
    </div>
  )
}
