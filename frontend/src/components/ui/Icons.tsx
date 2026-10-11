// Small, consistent stroke-icon set (20px, 1.6 stroke) - hand-rolled rather
// than adding a new icon-library dependency this late, but kept to one
// uniform style throughout rather than mixing in emoji/unicode glyphs.
import type { SVGProps } from 'react'

type IconProps = SVGProps<SVGSVGElement>

const base = {
  width: 18, height: 18, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor',
  strokeWidth: 1.6, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const,
}

export const HomeIcon = (p: IconProps) => (
  <svg {...base} {...p}><path d="M3 11.5 12 4l9 7.5" /><path d="M5.5 10v9.5a1 1 0 0 0 1 1H9.5v-6h5v6h3a1 1 0 0 0 1-1V10" /></svg>
)
export const JobsIcon = (p: IconProps) => (
  <svg {...base} {...p}><rect x="3.5" y="7.5" width="17" height="12" rx="1.8" /><path d="M8.5 7.5V6a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2v1.5" /><path d="M3.5 12.5h17" /></svg>
)
export const ProfileIcon = (p: IconProps) => (
  <svg {...base} {...p}><circle cx="12" cy="8" r="3.3" /><path d="M5 20c0-3.6 3.1-6.3 7-6.3s7 2.7 7 6.3" /></svg>
)
export const DocumentIcon = (p: IconProps) => (
  <svg {...base} {...p}><path d="M7 3.5h7l3 3v13.2a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4.5a1 1 0 0 1 1-1Z" /><path d="M14 3.5V7h3.2" /><path d="M9 12h6M9 15.3h6" /></svg>
)
export const ScannerIcon = (p: IconProps) => (
  <svg {...base} {...p}><circle cx="12" cy="12" r="8.5" /><circle cx="12" cy="12" r="3" /><path d="M12 3.5v2M12 18.5v2M3.5 12h2M18.5 12h2" /></svg>
)
export const MailIcon = (p: IconProps) => (
  <svg {...base} {...p}><rect x="3.5" y="5.5" width="17" height="13" rx="1.6" /><path d="m4.2 6.5 7 5.8 7-5.8" /></svg>
)
export const LinkedInIcon = (p: IconProps) => (
  <svg {...base} {...p}><rect x="3.5" y="3.5" width="17" height="17" rx="2.2" /><path d="M8 10.3v6.2M8 7.6v.1M12 16.5v-4a2 2 0 0 1 4 0v4M12 12.5v4" /></svg>
)
export const StackIcon = (p: IconProps) => (
  <svg {...base} {...p}><path d="m12 3.5 8 4.3-8 4.3-8-4.3 8-4.3Z" /><path d="m4 12.2 8 4.3 8-4.3M4 16.5l8 4.3 8-4.3" /></svg>
)
export const SettingsIcon = (p: IconProps) => (
  <svg {...base} {...p}><circle cx="12" cy="12" r="3" /><path d="M12 3.8v2.3M12 17.9v2.3M5.4 7.4l2 1.1M16.6 15.5l2 1.1M3.8 12h2.3M17.9 12h2.3M5.4 16.6l2-1.1M16.6 8.5l2-1.1" /></svg>
)
export const ChevronLeftIcon = (p: IconProps) => (
  <svg {...base} {...p}><path d="M15 5.5 8.5 12l6.5 6.5" /></svg>
)
