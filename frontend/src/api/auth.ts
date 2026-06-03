import client from './client'
import type { LoginRequest, TokenResponse, User } from '../types/auth'

export const authApi = {
  login: async (data: LoginRequest): Promise<TokenResponse> => {
    const res = await client.post<TokenResponse>('/auth/login', data)
    return res.data
  },

  me: async (): Promise<User> => {
    const res = await client.get<User>('/auth/me')
    return res.data
  },

  refresh: async (refresh_token: string): Promise<TokenResponse> => {
    const res = await client.post<TokenResponse>('/auth/refresh', { refresh_token })
    return res.data
  },
}
