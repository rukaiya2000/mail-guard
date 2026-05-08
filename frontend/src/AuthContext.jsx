import { createContext, useContext, useState, useEffect } from 'react'
import axios from 'axios'

const AuthContext = createContext()

const API_BASE_URL = 'http://localhost:8000'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check if returning from Google OAuth callback
    const urlParams = new URLSearchParams(window.location.search)
    const tokenFromUrl = urlParams.get('token')

    if (tokenFromUrl) {
      // Store token and clean up URL
      setToken(tokenFromUrl)
      localStorage.setItem('token', tokenFromUrl)
      verifyToken(tokenFromUrl)
      // Clean up URL without reload
      window.history.replaceState({}, document.title, window.location.pathname)
    } else {
      const savedToken = localStorage.getItem('token')
      if (savedToken) {
        setToken(savedToken)
        // Verify token is still valid
        verifyToken(savedToken)
      } else {
        setLoading(false)
      }
    }
  }, [])

  const verifyToken = async (authToken) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/me`, {
        headers: { Authorization: `Bearer ${authToken}` },
      })
      setUser(response.data)
    } catch (error) {
      localStorage.removeItem('token')
      setToken(null)
    } finally {
      setLoading(false)
    }
  }

  const loginWithGoogle = () => {
    window.location.href = `${API_BASE_URL}/auth/google`
  }

  const logout = () => {
    setUser(null)
    setToken(null)
    localStorage.removeItem('token')
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, loginWithGoogle, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
