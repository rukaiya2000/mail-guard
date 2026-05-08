export default function About() {
  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Hero Section */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-800 text-white rounded-lg p-12 text-center">
        <h1 className="text-4xl font-bold mb-4">SecureAI Sentinel</h1>
        <p className="text-xl mb-2">AI-Powered Email Threat Detection & LLM Monitoring</p>
        <p className="text-blue-100">Protecting your inbox with advanced machine learning</p>
      </div>

      {/* Overview */}
      <div className="bg-white border border-gray-200 rounded-lg p-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">About This Project</h2>
        <p className="text-gray-700 text-lg leading-relaxed">
          SecureAI Sentinel is a comprehensive AI security platform designed to detect and classify email threats
          in real-time. By leveraging advanced language models and comprehensive logging, this platform provides
          security analysts, organizations, and enterprises with powerful tools to protect their users from phishing
          attacks, spam, and malicious content.
        </p>
      </div>

      {/* Key Features */}
      <div className="bg-white border border-gray-200 rounded-lg p-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Key Features</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="border-l-4 border-blue-600 pl-4">
            <h3 className="font-bold text-gray-900 mb-2">🔍 Smart Email Classification</h3>
            <p className="text-gray-700">
              Automatically classify emails as phishing, spam, or legitimate using advanced AI models with confidence scoring.
            </p>
          </div>

          <div className="border-l-4 border-green-600 pl-4">
            <h3 className="font-bold text-gray-900 mb-2">📊 Real-time Monitoring</h3>
            <p className="text-gray-700">
              Monitor LLM API performance with live dashboards showing latency, token usage, and cost tracking.
            </p>
          </div>

          <div className="border-l-4 border-purple-600 pl-4">
            <h3 className="font-bold text-gray-900 mb-2">⚡ Batch Processing</h3>
            <p className="text-gray-700">
              Process up to 50 emails simultaneously. Upload CSV files or paste emails for rapid threat analysis.
            </p>
          </div>

          <div className="border-l-4 border-red-600 pl-4">
            <h3 className="font-bold text-gray-900 mb-2">📈 Advanced Analytics</h3>
            <p className="text-gray-700">
              View detailed threat distribution charts, hourly trends, and peak activity analysis with 24-hour trends.
            </p>
          </div>

          <div className="border-l-4 border-yellow-600 pl-4">
            <h3 className="font-bold text-gray-900 mb-2">🔐 Secure Authentication</h3>
            <p className="text-gray-700">
              User registration and JWT-based authentication with per-user data isolation and activity logging.
            </p>
          </div>

          <div className="border-l-4 border-indigo-600 pl-4">
            <h3 className="font-bold text-gray-900 mb-2">📧 Email Header Parsing</h3>
            <p className="text-gray-700">
              Extract and validate email headers. Identify suspicious senders and analyze email structure automatically.
            </p>
          </div>
        </div>
      </div>

      {/* Technology Stack */}
      <div className="bg-white border border-gray-200 rounded-lg p-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Technology Stack</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <h3 className="font-bold text-gray-900 mb-3">Backend</h3>
            <ul className="text-gray-700 space-y-2">
              <li>✓ FastAPI - Modern Python framework</li>
              <li>✓ SQLAlchemy - ORM for databases</li>
              <li>✓ SQLite - Lightweight database</li>
              <li>✓ OpenAI API - LLM integration</li>
              <li>✓ JWT - Secure authentication</li>
              <li>✓ Pandas & ReportLab - Data export</li>
            </ul>
          </div>

          <div>
            <h3 className="font-bold text-gray-900 mb-3">Frontend</h3>
            <ul className="text-gray-700 space-y-2">
              <li>✓ React 18 - UI framework</li>
              <li>✓ Vite - Fast build tool</li>
              <li>✓ Tailwind CSS - Styling</li>
              <li>✓ Recharts - Data visualization</li>
              <li>✓ Axios - HTTP client</li>
              <li>✓ Context API - State management</li>
            </ul>
          </div>

          <div>
            <h3 className="font-bold text-gray-900 mb-3">Features</h3>
            <ul className="text-gray-700 space-y-2">
              <li>✓ Dark Mode Support</li>
              <li>✓ CSV/PDF Export</li>
              <li>✓ Email Caching</li>
              <li>✓ Performance Optimization</li>
              <li>✓ Activity Logging</li>
              <li>✓ Date Range Filtering</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Use Cases */}
      <div className="bg-white border border-gray-200 rounded-lg p-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Use Cases</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-gray-50 p-4 rounded-lg">
            <h3 className="font-bold text-gray-900 mb-2">Enterprise Security</h3>
            <p className="text-gray-700 text-sm">
              Protect entire organizations from phishing attacks and email-based threats with centralized monitoring.
            </p>
          </div>

          <div className="bg-gray-50 p-4 rounded-lg">
            <h3 className="font-bold text-gray-900 mb-2">Security Teams</h3>
            <p className="text-gray-700 text-sm">
              Analyze suspicious emails quickly with detailed threat classifications and confidence scores.
            </p>
          </div>

          <div className="bg-gray-50 p-4 rounded-lg">
            <h3 className="font-bold text-gray-900 mb-2">LLM Integration</h3>
            <p className="text-gray-700 text-sm">
              Monitor and track LLM API usage, costs, and performance across your security infrastructure.
            </p>
          </div>

          <div className="bg-gray-50 p-4 rounded-lg">
            <h3 className="font-bold text-gray-900 mb-2">Security Research</h3>
            <p className="text-gray-700 text-sm">
              Study email threat patterns and analyze malicious content with historical data and analytics.
            </p>
          </div>
        </div>
      </div>

      {/* How It Works */}
      <div className="bg-white border border-gray-200 rounded-lg p-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">How It Works</h2>
        <div className="space-y-4">
          <div className="flex gap-4">
            <div className="flex-shrink-0 bg-blue-600 text-white rounded-full w-10 h-10 flex items-center justify-center font-bold">
              1
            </div>
            <div>
              <h3 className="font-bold text-gray-900">Submit Email</h3>
              <p className="text-gray-700">
                Paste or upload email content through the user-friendly interface.
              </p>
            </div>
          </div>

          <div className="flex gap-4">
            <div className="flex-shrink-0 bg-blue-600 text-white rounded-full w-10 h-10 flex items-center justify-center font-bold">
              2
            </div>
            <div>
              <h3 className="font-bold text-gray-900">Parse Headers</h3>
              <p className="text-gray-700">
                Extract sender, recipient, subject, and other email metadata.
              </p>
            </div>
          </div>

          <div className="flex gap-4">
            <div className="flex-shrink-0 bg-blue-600 text-white rounded-full w-10 h-10 flex items-center justify-center font-bold">
              3
            </div>
            <div>
              <h3 className="font-bold text-gray-900">AI Classification</h3>
              <p className="text-gray-700">
                Send to LLM with specialized prompt to classify threat type and confidence.
              </p>
            </div>
          </div>

          <div className="flex gap-4">
            <div className="flex-shrink-0 bg-blue-600 text-white rounded-full w-10 h-10 flex items-center justify-center font-bold">
              4
            </div>
            <div>
              <h3 className="font-bold text-gray-900">Log & Analyze</h3>
              <p className="text-gray-700">
                Store results in database with API performance metrics and cost tracking.
              </p>
            </div>
          </div>

          <div className="flex gap-4">
            <div className="flex-shrink-0 bg-blue-600 text-white rounded-full w-10 h-10 flex items-center justify-center font-bold">
              5
            </div>
            <div>
              <h3 className="font-bold text-gray-900">View Results</h3>
              <p className="text-gray-700">
                See classification results, analytics, and historical data in real-time dashboards.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 text-center">
          <p className="text-3xl font-bold text-blue-600">4</p>
          <p className="text-gray-700 text-sm mt-2">Main Tabs</p>
        </div>

        <div className="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
          <p className="text-3xl font-bold text-green-600">15+</p>
          <p className="text-gray-700 text-sm mt-2">API Endpoints</p>
        </div>

        <div className="bg-purple-50 border border-purple-200 rounded-lg p-6 text-center">
          <p className="text-3xl font-bold text-purple-600">50</p>
          <p className="text-gray-700 text-sm mt-2">Emails/Batch</p>
        </div>

        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <p className="text-3xl font-bold text-red-600">3</p>
          <p className="text-gray-700 text-sm mt-2">Threat Types</p>
        </div>
      </div>

      {/* Getting Started */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Get Started</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h3 className="font-bold text-gray-900 mb-3">Requirements</h3>
            <ul className="text-gray-700 space-y-2">
              <li>✓ Python 3.8+</li>
              <li>✓ Node.js 16+</li>
              <li>✓ OpenAI API Key</li>
              <li>✓ Modern web browser</li>
            </ul>
          </div>

          <div>
            <h3 className="font-bold text-gray-900 mb-3">Quick Setup</h3>
            <ol className="text-gray-700 space-y-2 list-decimal list-inside">
              <li>Backend: pip install -r requirements.txt</li>
              <li>Frontend: npm install</li>
              <li>Backend: python main.py</li>
              <li>Frontend: npm run dev</li>
            </ol>
          </div>
        </div>
        <p className="text-gray-700 mt-4">
          For detailed setup instructions, see <span className="font-semibold">SETUP.md</span> in the project root.
        </p>
      </div>

      {/* Footer */}
      <div className="text-center text-gray-600 border-t pt-8">
        <p className="mb-2">
          <span className="font-semibold">SecureAI Sentinel v1.0</span>
        </p>
        <p>
          Built with FastAPI, React, and advanced AI models for enterprise email security.
        </p>
        <p className="text-sm mt-4">
          © 2024 SecureAI Sentinel. All rights reserved.
        </p>
      </div>
    </div>
  )
}
