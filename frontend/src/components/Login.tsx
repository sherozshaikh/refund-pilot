import { useState, type FormEvent } from 'react'
import { apiClient } from '../lib/api'

interface Props {
  onSuccess: () => void
}

export function Login({ onSuccess }: Props) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const params = new URLSearchParams()
      params.append('username', username)
      params.append('password', password)
      const { data } = await apiClient.post<{ access_token: string }>(
        '/api/v1/auth/login',
        params,
        { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } },
      )
      localStorage.setItem('admin_token', data.access_token)
      onSuccess()
    } catch {
      setError('Invalid credentials')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-lg border bg-white p-8 shadow-sm"
      >
        <h2 className="mb-6 text-xl font-semibold text-gray-900">Admin Login</h2>

        {error && (
          <p className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>
        )}

        <label className="block text-sm font-medium text-gray-700">
          Username
          <input
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            autoFocus
          />
        </label>

        <label className="mt-4 block text-sm font-medium text-gray-700">
          Password
          <input
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>

        <button
          type="submit"
          disabled={loading}
          className="mt-6 w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </div>
  )
}
