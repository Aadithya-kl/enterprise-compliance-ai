import { useAuth } from '../store/authStore'
import { formatDate, formatRole } from '../utils/formatters'

export default function SettingsPage() {
  const { user } = useAuth()

  const ENV_INFO = [
    { label: 'API Endpoint',      value: import.meta.env.VITE_API_URL ?? 'http://localhost:8000' },
    { label: 'Environment',       value: import.meta.env.MODE },
  ]

  return (
    <div className="max-w-2xl space-y-5">
      <div>
        <h1 className="page-heading">Settings</h1>
        <p className="page-subheading mt-1">
          Account information and platform configuration.
        </p>
      </div>

      {/* Profile */}
      <div className="card p-5">
        <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Profile</h2>
        <div className="flex items-center gap-4 mb-5">
          <div className="w-14 h-14 rounded-full bg-brand-600/20 border border-brand-600/30 flex items-center justify-center">
            <span className="text-xl font-bold text-brand-400">
              {user?.full_name?.charAt(0).toUpperCase()}
            </span>
          </div>
          <div>
            <p className="font-semibold text-gray-900 dark:text-white">{user?.full_name}</p>
            <p className="text-sm text-gray-500">{user?.email}</p>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-xs text-gray-500 mb-0.5">Role</p>
            <p className="font-medium text-gray-900 dark:text-white">{formatRole(user?.role ?? '')}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-0.5">Account Status</p>
            <p className="font-medium text-green-600 dark:text-green-400">Active</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-0.5">Member Since</p>
            <p className="font-medium text-gray-900 dark:text-white">{formatDate(user?.created_at ?? '')}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-0.5">Last Login</p>
            <p className="font-medium text-gray-900 dark:text-white">
              {user?.last_login_at ? formatDate(user.last_login_at) : 'N/A'}
            </p>
          </div>
        </div>
      </div>

      {/* Platform info */}
      <div className="card p-5">
        <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Platform Configuration</h2>
        <div className="space-y-3">
          {ENV_INFO.map((item) => (
            <div key={item.label} className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-800 last:border-0">
              <span className="text-sm text-gray-500">{item.label}</span>
              <span className="text-sm font-mono text-gray-900 dark:text-gray-100 bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded">
                {item.value}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="card p-5">
        <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">Password</h2>
        <p className="text-xs text-gray-500 mb-3">
          To change your password, contact your platform administrator.
        </p>
      </div>
    </div>
  )
}
