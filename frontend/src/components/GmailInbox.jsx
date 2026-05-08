import { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000'

const getLabelColor = (label) => {
  switch (label) {
    case 'LEGITIMATE':
      return 'bg-green-100 text-green-800'
    case 'SPAM':
      return 'bg-yellow-100 text-yellow-800'
    case 'PHISHING':
      return 'bg-red-100 text-red-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}

const getLabelEmoji = (label) => {
  switch (label) {
    case 'LEGITIMATE':
      return '✅'
    case 'SPAM':
      return '⚠️'
    case 'PHISHING':
      return '🚨'
    default:
      return '❓'
  }
}

export default function GmailInbox() {
  const [emails, setEmails] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [classifying, setClassifying] = useState({})
  const [results, setResults] = useState({})
  const [expandedReasons, setExpandedReasons] = useState({})

  useEffect(() => {
    fetchEmails()
  }, [])

  const fetchEmails = async () => {
    try {
      setLoading(true)
      const response = await axios.get(`${API_BASE_URL}/gmail/inbox`)
      setEmails(response.data.emails || [])
      setError(null)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch emails')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const classifyEmail = async (emailId, emailText) => {
    try {
      setClassifying({ ...classifying, [emailId]: true })
      const response = await axios.post(`${API_BASE_URL}/classify`, {
        email_text: emailText,
        gmail_message_id: emailId,
      })
      setResults({ ...results, [emailId]: response.data })
      setClassifying({ ...classifying, [emailId]: false })
    } catch (err) {
      console.error('Classification failed:', err)
      setResults({
        ...results,
        [emailId]: { label: 'ERROR', confidence: 0, reasoning: err.response?.data?.detail || 'Failed to classify' },
      })
      setClassifying({ ...classifying, [emailId]: false })
    }
  }

  const toggleReason = (emailId) => {
    setExpandedReasons({
      ...expandedReasons,
      [emailId]: !expandedReasons[emailId],
    })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-gray-600">Loading your emails...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
        {error}
        <button
          onClick={fetchEmails}
          className="ml-4 underline hover:font-bold"
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">📧 Gmail Inbox</h2>
        <button
          onClick={fetchEmails}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
        >
          Refresh
        </button>
      </div>

      {emails.length === 0 ? (
        <div className="text-center py-12 text-gray-600">
          No emails found in your inbox
        </div>
      ) : (
        <div className="space-y-3">
          {emails.map((email) => (
            <div
              key={email.id}
              className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition"
            >
              <div className="flex justify-between items-start gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-semibold text-gray-900 truncate">
                      {email.from}
                    </span>
                    <span className="text-sm text-gray-500">({email.date})</span>
                  </div>
                  <h3 className="font-medium text-gray-900 mb-1 truncate">
                    {email.subject}
                  </h3>
                  <p className="text-sm text-gray-600 line-clamp-2">
                    {email.snippet}
                  </p>
                </div>

                <div className="flex flex-col items-end gap-2 flex-shrink-0">
                  {results[email.id] ? (
                    <div className="space-y-1 text-right">
                      <div
                        className={`px-3 py-1 rounded-full text-sm font-medium ${getLabelColor(
                          results[email.id].label
                        )}`}
                      >
                        {getLabelEmoji(results[email.id].label)}{' '}
                        {results[email.id].label}
                      </div>
                      <div className="text-xs text-gray-600">
                        {(results[email.id].confidence * 100).toFixed(0)}% confident
                      </div>
                      <button
                        onClick={() => toggleReason(email.id)}
                        className="text-xs text-blue-600 hover:underline"
                      >
                        {expandedReasons[email.id] ? 'Hide' : 'Show'} reason
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => classifyEmail(email.id, email.body)}
                      disabled={classifying[email.id]}
                      className={`px-4 py-2 rounded-lg font-medium transition ${
                        classifying[email.id]
                          ? 'bg-gray-300 text-gray-600 cursor-not-allowed'
                          : 'bg-blue-600 text-white hover:bg-blue-700'
                      }`}
                    >
                      {classifying[email.id] ? 'Classifying...' : 'Classify'}
                    </button>
                  )}
                </div>
              </div>

              {results[email.id] && expandedReasons[email.id] && (
                <div className="mt-3 pt-3 border-t border-gray-200">
                  <p className="text-sm text-gray-700">
                    <strong>Reasoning:</strong> {results[email.id].reasoning}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
