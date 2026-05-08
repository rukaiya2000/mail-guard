import { useAuth } from '../AuthContext'

export default function Login() {
  const { loginWithGoogle } = useAuth()

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="bg-white p-8 rounded-lg shadow-lg w-full max-w-md text-center">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">SecureAI Sentinel</h1>
        <p className="text-gray-600 mb-12">Email threat detection & LLM monitoring</p>

        <button
          onClick={loginWithGoogle}
          className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 transition flex items-center justify-center gap-2"
        >
          <span>🔐</span> Continue with Google
        </button>

        <p className="text-gray-500 text-sm mt-6">
          Sign in securely with your Google account
        </p>
      </div>
    </div>
  )
}
