// Shared tab bar - replaces the identical inline markup that was
// duplicated between the Job workspace and Career Profile pages.
export default function Tabs({
  tabs, active, onChange,
}: { tabs: string[]; active: string; onChange: (t: string) => void }) {
  return (
    <div role="tablist" className="flex gap-1 mb-6 overflow-x-auto -mx-1 px-1">
      {tabs.map((t) => (
        <button
          key={t}
          role="tab"
          aria-selected={active === t}
          onClick={() => onChange(t)}
          className={`px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-1 ${
            active === t ? 'bg-brand-700 text-white' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
          }`}
        >
          {t}
        </button>
      ))}
    </div>
  )
}
