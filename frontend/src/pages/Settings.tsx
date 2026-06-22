import { useState, useEffect } from 'react'
import { useAuth } from '../store/authStore'
import { formatDate, formatRole } from '../utils/formatters'
import { integrationsApi } from '../api/integrations'
import { extractErrorMessage } from '../utils/errors'

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
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
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

      {/* Integrations */}
      <IntegrationsPanel />

      <div className="card p-5">
        <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">Password</h2>
        <p className="text-xs text-gray-500 mb-3">
          To change your password, contact your platform administrator.
        </p>
      </div>
    </div>
  )
}

function IntegrationsPanel() {
  const [gdriveStatus, setGdriveStatus] = useState<{ connected: boolean, message?: string } | null>(null)
  const [notionStatus, setNotionStatus] = useState<{ connected: boolean, message?: string } | null>(null)
  const [syncingGdrive, setSyncingGdrive] = useState(false)
  const [syncingNotion, setSyncingNotion] = useState(false)
  const [gdriveEnabled, setGdriveEnabled] = useState(false)
  const [notionEnabled, setNotionEnabled] = useState(false)
  const [loadingConfig, setLoadingConfig] = useState(true)

  useEffect(() => {
    const fetchConfigs = async () => {
      try {
        const configs = await integrationsApi.getIntegrations()
        setGdriveEnabled(!!configs.google_drive)
        setNotionEnabled(!!configs.notion)
      } catch (err) {
        console.error('Failed to fetch integration toggles', err)
      } finally {
        setLoadingConfig(false)
      }
    }
    fetchConfigs()
  }, [])

  const verifyGdrive = async () => {
    try {
      const res = await integrationsApi.verifyGoogleDrive()
      setGdriveStatus(res)
    } catch (err) {
      setGdriveStatus({ connected: false, message: extractErrorMessage(err) ?? 'Verification failed' })
    }
  }

  const verifyNotion = async () => {
    try {
      const res = await integrationsApi.verifyNotion()
      setNotionStatus(res)
    } catch (err) {
      setNotionStatus({ connected: false, message: extractErrorMessage(err) ?? 'Verification failed' })
    }
  }

  const syncGdrive = async () => {
    setSyncingGdrive(true)
    try {
      await integrationsApi.syncGoogleDrive()
      alert('Google Drive sync successful!')
    } catch (err) {
      alert(extractErrorMessage(err) ?? 'Google Drive sync failed.')
    } finally {
      setSyncingGdrive(false)
    }
  }

  const syncNotion = async () => {
    setSyncingNotion(true)
    try {
      await integrationsApi.syncNotion()
      alert('Notion sync successful!')
    } catch (err) {
      alert(extractErrorMessage(err) ?? 'Notion sync failed.')
    } finally {
      setSyncingNotion(false)
    }
  }

  const toggleGdrive = async () => {
    const nextState = !gdriveEnabled
    setGdriveEnabled(nextState)
    try {
      await integrationsApi.toggleIntegration('google_drive', nextState)
      if (!nextState) {
        setGdriveStatus(null)
      }
    } catch (err) {
      alert(extractErrorMessage(err) ?? 'Failed to toggle Google Drive integration.')
      setGdriveEnabled(!nextState)
    }
  }

  const toggleNotion = async () => {
    const nextState = !notionEnabled
    setNotionEnabled(nextState)
    try {
      await integrationsApi.toggleIntegration('notion', nextState)
      if (!nextState) {
        setNotionStatus(null)
      }
    } catch (err) {
      alert(extractErrorMessage(err) ?? 'Failed to toggle Notion integration.')
      setNotionEnabled(!nextState)
    }
  }

  if (loadingConfig) {
    return <div className="text-sm text-gray-500 dark:text-gray-400">Loading integrations panel...</div>
  }

  return (
    <>
      <div className="card p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Google Drive Integration</h2>
          <div className="flex items-center gap-3">
            <button
              onClick={toggleGdrive}
              disabled={user?.role !== 'admin'}
              className={`relative inline-flex h-5 w-9 shrink-0 rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${gdriveEnabled ? 'bg-brand-600' : 'bg-gray-200 dark:bg-gray-700'} ${user?.role !== 'admin' ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
              aria-label="Toggle Google Drive"
            >
              <span className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${gdriveEnabled ? 'translate-x-4' : 'translate-x-0'}`} />
            </button>
            <span className={`text-xs px-2 py-1 rounded-full ${gdriveEnabled && gdriveStatus?.connected ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
              {!gdriveEnabled ? 'Deactivated' : gdriveStatus?.connected ? 'Connected' : 'Not Verified'}
            </span>
          </div>
        </div>
        <p className="text-xs text-gray-500 mb-4">
          {gdriveStatus?.message || 'Sync compliance documents directly from Google Drive.'}
        </p>
        <div className="flex flex-col sm:flex-row gap-3">
          <button onClick={verifyGdrive} disabled={!gdriveEnabled} className="btn btn-secondary text-xs py-1.5 disabled:opacity-50">Verify Connection</button>
          <button onClick={syncGdrive} disabled={!gdriveEnabled || syncingGdrive} className="btn btn-primary text-xs py-1.5 disabled:opacity-50">
            {syncingGdrive ? 'Syncing...' : 'Sync Documents'}
          </button>
        </div>
      </div>

      <div className="card p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Notion Integration</h2>
          <div className="flex items-center gap-3">
            <button
              onClick={toggleNotion}
              disabled={user?.role !== 'admin'}
              className={`relative inline-flex h-5 w-9 shrink-0 rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${notionEnabled ? 'bg-brand-600' : 'bg-gray-200 dark:bg-gray-700'} ${user?.role !== 'admin' ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
              aria-label="Toggle Notion"
            >
              <span className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${notionEnabled ? 'translate-x-4' : 'translate-x-0'}`} />
            </button>
            <span className={`text-xs px-2 py-1 rounded-full ${notionEnabled && notionStatus?.connected ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
              {!notionEnabled ? 'Deactivated' : notionStatus?.connected ? 'Connected' : 'Not Verified'}
            </span>
          </div>
        </div>
        <p className="text-xs text-gray-500 mb-4">
          {notionStatus?.message || 'Sync compliance policies directly from Notion databases.'}
        </p>
        <div className="flex flex-col sm:flex-row gap-3">
          <button onClick={verifyNotion} disabled={!notionEnabled} className="btn btn-secondary text-xs py-1.5 disabled:opacity-50">Verify Connection</button>
          <button onClick={syncNotion} disabled={!notionEnabled || syncingNotion} className="btn btn-primary text-xs py-1.5 disabled:opacity-50">
            {syncingNotion ? 'Syncing...' : 'Sync Documents'}
          </button>
        </div>
      </div>
    </>
  )
}
