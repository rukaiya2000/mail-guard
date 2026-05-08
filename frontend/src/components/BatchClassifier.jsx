import { useState } from 'react'
import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000'

export default function BatchClassifier() {
  const [emails, setEmails] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [stats, setStats] = useState(null)

  const handleFileUpload = (e) => {
    const file = e.target.files[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (event) => {
      const content = event.target.result
      const lines = content.split('\n').filter(line => line.trim())
      setEmails(lines.join('\n'))
    }
    reader.readAsText(file)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const emailList = emails
      .split('\n')
      .map(e => e.trim())
      .filter(e => e.length > 0)

    if (emailList.length === 0) {
      setError('Please enter at least one email')
      return
    }

    if (emailList.length > 50) {
      setError('Maximum 50 emails per batch')
      return
    }

    try {
      setLoading(true)
      setError(null)
      const response = await axios.post(`${API_BASE_URL}/classify-batch`, {
        emails: emailList,
      })

      setResults(response.data.results)

      // Calculate stats
      const successful = response.data.results.filter(r => r.success)
      const phishing = successful.filter(r => r.data.label === 'PHISHING').length
      const spam = successful.filter(r => r.data.label === 'SPAM').length
      const legitimate = successful.filter(r => r.data.label === 'LEGITIMATE').length

      setStats({
        total: response.data.total,
        successful: successful.length,
        failed: response.data.results.filter(r => !r.success).length,
        phishing,
        spam,
        legitimate,
        avgConfidence: (
          successful.reduce((sum, r) => sum + r.data.confidence, 0) / successful.length
        ).toFixed(2),
      })
    } catch (err) {
      setError(err.response?.data?.detail || 'Batch classification failed')
    } finally {
      setLoading(false)
    }
  }

  const getLabelColor = (label) => {
    switch (label.toUpperCase()) {
      case 'PHISHING':
        return 'bg-red-100 text-red-800'
      case 'SPAM':
        return 'bg-yellow-100 text-yellow-800'
      case 'LEGITIMATE':
        return 'bg-green-100 text-green-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className="space-y-6">
      {/* Input Section */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-xl font-bold mb-4 text-gray-800">Batch Email Classifier</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Upload CSV or Enter Emails (one per line, max 50)
            </label>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <input
                  type="file"
                  accept=".csv,.txt"
                  onChange={handleFileUpload}
                  className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                />
              </div>
              <p className="text-gray-500 text-sm flex items-center">or paste below</p>
            </div>
            <textarea
              value={emails}
              onChange={(e) => setEmails(e.target.value)}
              placeholder="Paste emails, one per line. Each line should be a complete email..."
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
            {loading ? 'Processing...' : 'Classify Batch'}
          </button>
        </form>
      </div>

      {/* Stats Summary */}
      {stats && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h3 className="text-lg font-bold mb-4 text-gray-800">Batch Results Summary</h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="bg-blue-50 p-4 rounded-lg">
              <p className="text-gray-600 text-xs font-medium">Total Processed</p>
              <p className="text-blue-700 font-bold text-lg">{stats.total}</p>
            </div>
            <div className="bg-green-50 p-4 rounded-lg">
              <p className="text-gray-600 text-xs font-medium">Successful</p>
              <p className="text-green-700 font-bold text-lg">{stats.successful}</p>
            </div>
            <div className="bg-red-50 p-4 rounded-lg">
              <p className="text-gray-600 text-xs font-medium">Phishing</p>
              <p className="text-red-700 font-bold text-lg">{stats.phishing}</p>
            </div>
            <div className="bg-yellow-50 p-4 rounded-lg">
              <p className="text-gray-600 text-xs font-medium">Spam</p>
              <p className="text-yellow-700 font-bold text-lg">{stats.spam}</p>
            </div>
            <div className="bg-purple-50 p-4 rounded-lg">
              <p className="text-gray-600 text-xs font-medium">Avg Confidence</p>
              <p className="text-purple-700 font-bold text-lg">{stats.avgConfidence}</p>
            </div>
          </div>
        </div>
      )}

      {/* Results Table */}
      {results.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <div className="p-6 border-b border-gray-200">
            <h3 className="text-lg font-bold text-gray-800">Detailed Results</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">#</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Status</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Label</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Confidence</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Details</th>
                </tr>
              </thead>
              <tbody>
                {results.map((result, idx) => (
                  <tr key={idx} className="border-b border-gray-200 hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm text-gray-600">{idx + 1}</td>
                    <td className="px-6 py-4 text-sm">
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${
                          result.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {result.success ? 'Success' : 'Failed'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm">
                      {result.success && (
                        <span className={`px-2 py-1 rounded text-xs font-medium ${getLabelColor(result.data.label)}`}>
                          {result.data.label}
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {result.success && `${(result.data.confidence * 100).toFixed(1)}%`}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {result.success ? result.data.reasoning.substring(0, 50) : result.error}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
