export default function MetricCard({ title, value, unit = '', color = 'blue' }) {
  const colorClasses = {
    blue: 'bg-blue-50 border-blue-200',
    green: 'bg-green-50 border-green-200',
    red: 'bg-red-50 border-red-200',
    yellow: 'bg-yellow-50 border-yellow-200',
  }

  const textColorClasses = {
    blue: 'text-blue-700',
    green: 'text-green-700',
    red: 'text-red-700',
    yellow: 'text-yellow-700',
  }

  return (
    <div className={`${colorClasses[color]} border rounded-lg p-6`}>
      <p className="text-gray-600 text-sm font-medium mb-2">{title}</p>
      <p className={`${textColorClasses[color]} text-3xl font-bold`}>
        {value}
        <span className="text-lg ml-1">{unit}</span>
      </p>
    </div>
  )
}
