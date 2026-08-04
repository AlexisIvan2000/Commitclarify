import { forwardRef } from 'react'
import {
  ArrowDown2,
  ArrowLeft2,
  ArrowRight2,
  Book1,
  Calendar,
  ChartSquare,
  Clock,
  CloseCircle,
  Code1,
  Cpu,
  Danger,
  Data,
  DocumentCode,
  DocumentDownload,
  DocumentText,
  Export,
  Eye,
  EyeSlash,
  Flash,
  Folder2,
  Global,
  Hierarchy,
  Import,
  InfoCircle,
  Lock,
  Logout,
  MagicStar,
  Refresh,
  ScanBarcode,
  SearchNormal1,
  ShieldTick,
  Sms,
  TickCircle,
  Trash,
  User,
  Warning2,
} from 'iconsax-react'

function themed(Source) {
  const Themed = forwardRef(function ThemedIcon(props, ref) {
    return <Source ref={ref} variant="Linear" color="currentColor" size={18} {...props} />
  })

  Themed.displayName = `Themed(${Source.displayName || 'Icon'})`

  return Themed
}

export const Icons = {
  repos: themed(Folder2),
  scan: themed(ScanBarcode),
  report: themed(DocumentText),
  history: themed(Clock),
  account: themed(User),

  secrets_detection: themed(ShieldTick),
  gitignore_check: themed(Folder2),
  quality_check: themed(ChartSquare),
  readme_check: themed(Book1),

  clean: themed(TickCircle),
  issues_found: themed(Warning2),
  partial: themed(InfoCircle),
  unavailable: themed(EyeSlash),
  error: themed(CloseCircle),
  critical: themed(Danger),

  scanned: themed(ScanBarcode),
  completed: themed(TickCircle),
  scanning: themed(Refresh),
  analyzing: themed(Refresh),
  processing: themed(Refresh),
  pending: themed(Clock),
  failed: themed(CloseCircle),

  fetching: themed(Import),
  indexing: themed(Data),
  aiAnalyzing: themed(Cpu),
  done: themed(TickCircle),

  triage: themed(MagicStar),
  running: themed(Refresh),
  retry: themed(Refresh),
  view: themed(Eye),
  search: themed(SearchNormal1),
  trash: themed(Trash),
  logout: themed(Logout),
  exportPdf: themed(DocumentDownload),
  exportJson: themed(DocumentCode),
  download: themed(Export),

  commit: themed(Hierarchy),
  code: themed(Code1),
  test: themed(Flash),
  quota: themed(Flash),
  mail: themed(Sms),
  calendar: themed(Calendar),
  language: themed(Global),
  private: themed(Lock),
  public: themed(Global),
  hidden: themed(EyeSlash),

  back: themed(ArrowLeft2),
  forward: themed(ArrowRight2),
  expand: themed(ArrowDown2),
  collapse: themed(ArrowRight2),
}
