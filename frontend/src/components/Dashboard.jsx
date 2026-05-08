import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import MetricCard from './MetricCard'
import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000'

export default function Dashboard() {
  const [metrics, setMetrics] = useState({
    total_calls: 0,
    average_latency_ms: 0,
    error_rate: 0,
    total_tokens_used: 0,
    estimated_cost: 0,
  })
  const [chartData, setChartData] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        setLoading(true)
        const response = await axios.get(`${API_BASE_URL}/metrics`)
        setMetrics(response.data)

        // Store latency for chart (keep last 20 calls)
        setChartData((prev) => {
          const newData = [
            ...prev,
            { time: new Date().toLocaleTimeString(), latency: response.data.average_latency_ms },
          ]
          return newData.slice(-20)
        })
      } catch (error) {
        console.error('Failed to fetch metrics:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchMetrics()
    const interval = setInterval(fetchMetrics, 10000) // Poll every 10 seconds

    return () => clearInterval(interval)
  }, [])

  return (
    <div className="space-y-6">
      {/* Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Calls"
          value={metrics.total_calls}
          color="blue"
        />
        <MetricCard
          title="Avg Latency"
          value={metrics.average_latency_ms.toFixed(2)}
          unit="ms"
          color="green"
        />
        <MetricCard
          title="Error Rate"
          value={metrics.error_rate.toFixed(2)}
          unit="%"
          color={metrics.error_rate > 5 ? 'red' : 'yellow'}
        />
        <MetricCard
          title="Est. Cost"
          value={`$${metrics.estimated_cost.toFixed(4)}`}
          color="blue"
        />
      </div>

      {/* Latency Chart */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-xl font-bold mb-4 text-gray-800">Latency Trend (Last 20 Calls)</h2>
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="time" stroke="#6b7280" />
              <YAxis stroke="#6b7280" label={{ value: 'Latency (ms)', angle: -90, position: 'insideLeft' }} />
              <Tooltip contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb' }} />
              <Line
                type="monotone"
                dataKey="latency"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={{ fill: '#3b82f6', r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="text-center text-gray-500 py-12">
            No data yet. Make some classifications to see the chart.
          </div>
        )}
      </div>
    </div>
  )
}
