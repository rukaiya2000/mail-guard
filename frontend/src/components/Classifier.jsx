import { useState } from 'react'
import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000'

export default function Classifier() {
  const [emailText, setEmailText] = useState('')
  const [result, setResult] = useState(null)
  const [parsedEmail, setParsedEmail] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const getLabelColor = (label) => {
    switch (label.toUpperCase()) {
      case 'PHISHING':
        return { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700', badge: 'bg-red-100 text-red-800' }
      case 'SPAM':
        return { bg: 'bg-yellow-50', border: 'border-yellow-200', text: 'text-yellow-700', badge: 'bg-yellow-100 text-yellow-800' }
      case 'LEGITIMATE':
        return { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700', badge: 'bg-green-100 text-green-800' }
      default:
        return { bg: 'bg-gray-50', border: 'border-gray-200', text: 'text-gray-700', badge: 'bg-gray-100 text-gray-800' }
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!emailText.trim()) {
      setError('Please enter an email to classify')
      return
    }

    try {
      setLoading(true)
      setError(null)

      // Parse email headers
      const parseResponse = await axios.post(`${API_BASE_URL}/parse-email`, {
        email_text: emailText,
      })
      setParsedEmail(parseResponse.data)

      // Classify email
      const classifyResponse = await axios.post(`${API_BASE_URL}/classify`, {
        email_text: emailText,
      })
      setResult(classifyResponse.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to classify email. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const colors = result ? getLabelColor(result.label) : null

  return (
    <div className="space-y-6">
      {/* Input Section */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-xl font-bold mb-4 text-gray-800">Email Threat Classifier</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Paste Email Content
            </label>
            <textarea
              value={emailText}
              onChange={(e) => setEmailText(e.target.value)}
              placeholder="Paste the full email content here (including headers if available)..."
              rows="8"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            />
          </div>
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-2 rounded-lg font-medium hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Classifying...' : 'Classify Email'}
          </button>
        </form>
      </div>

      {/* Parsed Email Headers */}
      {parsedEmail && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
          <h3 className="text-lg font-bold text-gray-800 mb-4">Email Headers</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(parsedEmail.headers).map(([key, value]) => (
              <div key={key}>
                <p className="text-gray-600 text-sm font-medium capitalize">{key.replace('_', ' ')}</p>
                <p className="text-gray-800 text-sm break-all">{value}</p>
              </div>
            ))}
          </div>
          {parsedEmail.extracted_addresses.length > 0 && (
            <div className="mt-4 pt-4 border-t border-gray-200">
              <p className="text-gray-600 text-sm font-medium">Extracted Email Addresses</p>
              <div className="flex flex-wrap gap-2 mt-2">
                {parsedEmail.extracted_addresses.map((addr, idx) => (
                  <span key={idx} className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-xs">
                    {addr}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Result Card */}
      {result && (
        <div className={`${colors.bg} border-2 ${colors.border} rounded-lg p-6`}>
          <div className="flex items-start justify-between mb-4">
            <h3 className={`text-lg font-bold ${colors.text}`}>Classification Result</h3>
            <span className={`px-4 py-2 rounded-full font-semibold ${colors.badge}`}>
              {result.label}
            </span>
          </div>
          <div className="space-y-3">
            <div>
              <p className="text-gray-600 text-sm font-medium mb-1">Confidence</p>
              <div className="flex items-center space-x-2">
                <div className="flex-grow bg-gray-300 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${colors.badge.split(' ')[0]}`}
                    style={{ width: `${result.confidence * 100}%` }}
                  />
                </div>
                <span className={`font-semibold ${colors.text}`}>
                  {(result.confidence * 100).toFixed(1)}%
                </span>
              </div>
            </div>
            <div>
              <p className="text-gray-600 text-sm font-medium mb-1">Reasoning</p>
              <p className="text-gray-700">{result.reasoning}</p>
            </div>
            <div className="grid grid-cols-2 gap-4 pt-3 border-t border-gray-300">
              <div>
                <p className="text-gray-600 text-xs font-medium">Processing Time</p>
                <p className="text-gray-800 font-semibold">{result.latency_ms.toFixed(2)}ms</p>
              </div>
              <div>
                <p className="text-gray-600 text-xs font-medium">Tokens Used</p>
                <p className="text-gray-800 font-semibold">{result.tokens_used}</p>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  )
}
