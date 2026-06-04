/**
 * Axios client with JWT injection and 401 handling.
 * All API modules import this instance — never create Axios instances elsewhere.
 */

import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
export const API_V1 = `${BASE_URL}/api/v1`

export const client = axios.create({
  baseURL: API_V1,
  timeout: 60_000,
  headers: { 'Content-Type': 'application/json' },
})

// Dedicated client for the long-running AI workflow endpoint.
// The full pipeline (ComplianceAgent + RiskAgent + ReportAgent) runs a single
// LLM call that can take up to 5 minutes on local hardware.
export const workflowClient = axios.create({
  baseURL: API_V1,
  timeout: 300_000, // 5 minutes
  headers: { 'Content-Type': 'application/json' },
})

// ---- Request interceptor: inject access token ----
const _injectToken = (config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}

client.interceptors.request.use(_injectToken)
workflowClient.interceptors.request.use(_injectToken)

// ---- Response interceptor: handle 401 globally ----
const _handle401 = (error: AxiosError) => {
  if (error.response?.status === 401) {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    // Hard redirect to login — avoids stale React state issues
    window.location.href = '/login'
  }
  return Promise.reject(error)
}

client.interceptors.response.use((response) => response, _handle401)
workflowClient.interceptors.response.use((response) => response, _handle401)

export default client
