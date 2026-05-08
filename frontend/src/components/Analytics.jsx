import { useEffect, useState } from 'react'
import { PieChart, Pie, Cell, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000'

export default function Analytics() {
  const [analytics, setAnalytics] = useState({
    distribution: {},
    trends: [],
    top_hours: [],
  })
  const [loading, setLoading] = useState(true)
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  const fetchAnalytics = async () => {
    try {
      setLoading(true)
      const params = new URLSearchParams()
      if (startDate) params.append('start_date', startDate)
      if (endDate) params.append('end_date', endDate)

      const response = await axios.get(`${API_BASE_URL}/analytics?${params}`)
      setAnalytics(response.data)
    } catch (error) {
      console.error('Failed to fetch analytics:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAnalytics()
    const interval = setInterval(fetchAnalytics, 30000)
    return () => clearInterval(interval)
  }, [startDate, endDate])

  const COLORS = {
    PHISHING: '#ef4444',
    SPAM: '#eab308',
    LEGITIMATE: '#22c55e',
  }

  const pieData = Object.entries(analytics.distribution).map(([label, value]) => ({
    name: label,
    value,
  }))

  const totalClassifications = Object.values(analytics.distribution).reduce((a, b) => a + b, 0)

  return (
    <div className="space-y-6">
      {/* Date Range Filter */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <h3 className="font-semibold text-gray-700 mb-3">Filter by Date Range</h3>
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
      </div>

      {/* Distribution */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Pie Chart */}
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-xl font-bold mb-4 text-gray-800">Classification Distribution</h2>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, value }) => `${name}: ${value}`}
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {pieData.map((entry) => (
                    <Cell key={`cell-${entry.name}`} fill={COLORS[entry.name]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="text-center text-gray-500 py-12">No data yet</div>
          )}
        </div>

        {/* Stats Cards */}
        <div className="space-y-4">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-gray-600 text-sm font-medium">Phishing Attempts</p>
            <p className="text-red-700 text-3xl font-bold">{analytics.distribution.PHISHING || 0}</p>
            <p className="text-red-600 text-xs mt-1">
              {totalClassifications > 0 ? ((analytics.distribution.PHISHING / totalClassifications) * 100).toFixed(1) : 0}% of total
            </p>
          </div>

          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p className="text-gray-600 text-sm font-medium">Spam Messages</p>
            <p className="text-yellow-700 text-3xl font-bold">{analytics.distribution.SPAM || 0}</p>
            <p className="text-yellow-600 text-xs mt-1">
              {totalClassifications > 0 ? ((analytics.distribution.SPAM / totalClassifications) * 100).toFixed(1) : 0}% of total
            </p>
          </div>

          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <p className="text-gray-600 text-sm font-medium">Legitimate Emails</p>
            <p className="text-green-700 text-3xl font-bold">{analytics.distribution.LEGITIMATE || 0}</p>
            <p className="text-green-600 text-xs mt-1">
              {totalClassifications > 0 ? ((analytics.distribution.LEGITIMATE / totalClassifications) * 100).toFixed(1) : 0}% of total
            </p>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-gray-600 text-sm font-medium">Total Classifications</p>
            <p className="text-blue-700 text-3xl font-bold">{totalClassifications}</p>
          </div>
        </div>
      </div>

      {/* Trends Chart */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-xl font-bold mb-4 text-gray-800">Classification Trends (Last 24 Hours)</h2>
        {analytics.trends.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={analytics.trends}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="time"
                stroke="#6b7280"
                tick={{ fontSize: 12 }}
              />
              <YAxis stroke="#6b7280" />
              <Tooltip contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb' }} />
              <Legend />
              <Line
                type="monotone"
                dataKey="count"
                stroke="#3b82f6"
                strokeWidth={2}
                name="Classifications"
                dot={{ fill: '#3b82f6', r: 4 }}
              />
              <Line
                type="monotone"
                dataKey="avg_confidence"
                stroke="#8b5cf6"
                strokeWidth={2}
                name="Avg Confidence"
                dot={{ fill: '#8b5cf6', r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="text-center text-gray-500 py-12">
            No trend data yet. Classifications will appear here.
          </div>
        )}
      </div>

      {/* Top Hours */}
      {analytics.top_hours.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-xl font-bold mb-4 text-gray-800">Peak Activity Hours</h2>
          <div className="space-y-2">
            {analytics.top_hours.map((hour, idx) => (
              <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="font-medium text-gray-700">{hour.time}</span>
                <div className="flex items-center space-x-3">
                  <div className="flex-grow bg-gray-300 rounded-full h-2 w-48">
                    <div
                      className="bg-blue-600 h-2 rounded-full"
                      style={{
                        width: `${(hour.count / Math.max(...analytics.top_hours.map(h => h.count))) * 100}%`,
                      }}
                    />
                  </div>
                  <span className="text-gray-600 text-sm font-semibold">{hour.count}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
