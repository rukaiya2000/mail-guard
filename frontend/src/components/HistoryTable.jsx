import { useEffect, useState } from 'react'
import axios from 'axios'
import { useDebounce } from '../hooks/useDebounce'

const API_BASE_URL = 'http://localhost:8000'

export default function HistoryTable({ refreshTrigger = 0 }) {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [filterLabel, setFilterLabel] = useState('ALL')
  const [searchText, setSearchText] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [confidenceMin, setConfidenceMin] = useState(0)

  // Debounce search and date inputs
  const debouncedSearch = useDebounce(searchText, 300)
  const debouncedStartDate = useDebounce(startDate, 300)
  const debouncedEndDate = useDebounce(endDate, 300)
  const debouncedConfidence = useDebounce(confidenceMin, 300)

  const fetchHistory = async () => {
    try {
      setLoading(true)
      const params = new URLSearchParams()
      if (filterLabel !== 'ALL') params.append('label', filterLabel)
      if (debouncedSearch) params.append('search', debouncedSearch)
      if (debouncedStartDate) params.append('start_date', debouncedStartDate)
      if (debouncedEndDate) params.append('end_date', debouncedEndDate)
      if (debouncedConfidence > 0) params.append('confidence_min', debouncedConfidence)

      const response = await axios.get(`${API_BASE_URL}/history?${params}`)
      setHistory(response.data.slice(0, 10))
    } catch (error) {
      console.error('Failed to fetch history:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchHistory()
  }, [filterLabel, debouncedSearch, debouncedStartDate, debouncedEndDate, debouncedConfidence, refreshTrigger])

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

  const handleExportCSV = async () => {
    try {
      const params = new URLSearchParams()
      if (filterLabel !== 'ALL') params.append('label', filterLabel)
      const response = await axios.get(`${API_BASE_URL}/export/csv?${params}`, {
        responseType: 'blob',
      })
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `classifications_${new Date().toISOString().split('T')[0]}.csv`)
      document.body.appendChild(link)
      link.click()
      link.parentElement.removeChild(link)
    } catch (error) {
      console.error('Failed to export CSV:', error)
    }
  }

  const handleExportPDF = async () => {
    try {
      const params = new URLSearchParams()
      if (filterLabel !== 'ALL') params.append('label', filterLabel)
      const response = await axios.get(`${API_BASE_URL}/export/pdf?${params}`, {
        responseType: 'blob',
      })
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `report_${new Date().toISOString().split('T')[0]}.pdf`)
      document.body.appendChild(link)
      link.click()
      link.parentElement.removeChild(link)
    } catch (error) {
      console.error('Failed to export PDF:', error)
    }
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      <div className="p-6 border-b border-gray-200">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold text-gray-800">Recent Classifications</h2>
          <div className="flex gap-2">
            <button
              onClick={handleExportCSV}
              className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700 transition"
              title="Export as CSV"
            >
              📊 CSV
            </button>
            <button
              onClick={handleExportPDF}
              className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700 transition"
              title="Export as PDF"
            >
              📄 PDF
            </button>
          </div>
        </div>

        {/* Search & Filter */}
        <div className="space-y-3">
          {/* Search */}
          <div>
            <input
              type="text"
              placeholder="Search email snippets..."
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Label Filter */}
          <div className="flex gap-2 flex-wrap">
            {['ALL', 'PHISHING', 'SPAM', 'LEGITIMATE'].map((label) => (
              <button
                key={label}
                onClick={() => setFilterLabel(label)}
                className={`px-4 py-1 rounded-full text-sm font-medium transition ${
                  filterLabel === label
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Date Range Filter */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Start Date</label>
              <input
                type="datetime-local"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">End Date</label>
              <input
                type="datetime-local"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Confidence Threshold */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Min Confidence: {(confidenceMin * 100).toFixed(0)}%
            </label>
            <input
              type="range"
              min="0"
              max="100"
              value={confidenceMin * 100}
              onChange={(e) => setConfidenceMin(parseInt(e.target.value) / 100)}
              className="w-full"
            />
          </div>
        </div>
      </div>
      {loading && !history.length ? (
        <div className="p-12 text-center text-gray-500">Loading...</div>
      ) : history.length === 0 ? (
        <div className="p-12 text-center text-gray-500">No classifications yet. Start by classifying an email.</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Timestamp</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Label</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Confidence</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">Email Snippet</th>
              </tr>
            </thead>
            <tbody>
              {history.map((item, idx) => (
                <tr key={idx} className="border-b border-gray-200 hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {new Date(item.timestamp).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${getLabelColor(item.label)}`}>
                      {item.label}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {(item.confidence * 100).toFixed(1)}%
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600 truncate max-w-xs">
                    {item.email_snippet}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
