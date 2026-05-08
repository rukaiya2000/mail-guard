import { useState } from 'react'
import Dashboard from './components/Dashboard'
import Classifier from './components/Classifier'
import BatchClassifier from './components/BatchClassifier'
import Analytics from './components/Analytics'
import About from './components/About'
import GmailInbox from './components/GmailInbox'
import Login from './components/Login'
import { useTheme } from './ThemeContext'
import { useAuth } from './AuthContext'

function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const { isDark, setIsDark } = useTheme()
  const { user, loading, logout } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="text-xl text-gray-600">Loading...</div>
      </div>
    )
  }

  if (!user) {
    return <Login />
  }

  return (
    <div className={`min-h-screen ${isDark ? 'dark bg-gray-900' : 'bg-gray-100'}`}>
      {/* Header */}
      <header className={`${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white'} shadow border-b`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex justify-between items-start">
            <div>
              <h1 className={`text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                SecureAI Sentinel
              </h1>
              <p className={`${isDark ? 'text-gray-400' : 'text-gray-600'} mt-1`}>
                Email threat detection & LLM monitoring
              </p>
            </div>
            <div className="flex items-center gap-4">
              <div className={`${isDark ? 'text-gray-300' : 'text-gray-600'} text-sm`}>
                Welcome, <span className="font-semibold">{user.username}</span>
              </div>
              <button
                onClick={() => setIsDark(!isDark)}
                className={`px-4 py-2 rounded-lg font-medium transition ${
                  isDark
                    ? 'bg-gray-700 text-yellow-400 hover:bg-gray-600'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                {isDark ? '☀️' : '🌙'}
              </button>
              <button
                onClick={logout}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition text-sm font-medium"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <div className={`${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'} border-b`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex space-x-8 overflow-x-auto" aria-label="Tabs">
            {['dashboard', 'gmail', 'classifier', 'batch', 'analytics', 'about'].map((tab) => {
              const labels = {
                dashboard: 'Dashboard',
                gmail: '📧 Gmail Inbox',
                classifier: 'Email Classifier',
                batch: 'Batch Classifier',
                analytics: 'Analytics',
                about: 'About',
              }
              return (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`py-4 px-1 border-b-2 font-medium text-sm transition-all whitespace-nowrap ${
                    activeTab === tab
                      ? 'border-blue-500 text-blue-600'
                      : isDark
                      ? 'border-transparent text-gray-400 hover:text-gray-300 hover:border-gray-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  {labels[tab]}
                </button>
              )
            })}
          </nav>
        </div>
      </div>

      {/* Main Content */}
      <main className={`${isDark ? 'dark' : ''} px-4 sm:px-6 lg:px-8 py-8`}>
        {activeTab === 'dashboard' && <div className="max-w-7xl mx-auto"><Dashboard /></div>}
        {activeTab === 'gmail' && <div className="max-w-7xl mx-auto"><GmailInbox /></div>}
        {activeTab === 'classifier' && <div className="max-w-7xl mx-auto"><Classifier /></div>}
        {activeTab === 'batch' && <div className="max-w-7xl mx-auto"><BatchClassifier /></div>}
        {activeTab === 'analytics' && <div className="max-w-7xl mx-auto"><Analytics /></div>}
        {activeTab === 'about' && <About />}
      </main>
    </div>
  )
}

export default App
