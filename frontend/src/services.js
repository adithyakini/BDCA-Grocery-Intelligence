import axios from 'axios'

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api', timeout: 15000 })
export const getDashboard = async () => (await api.get('/dashboard')).data
export const getOffers = async (params = {}) => (await api.get('/offers', { params })).data
export const reviewOffer = async (id, status, note = '') => (await api.post(`/offers/${id}/review`, { status, note })).data
export const addDemoOffer = async () => (await api.post('/offers/demo')).data
export const createOffer = async (offer) => (await api.post('/offers', offer)).data
export const healthCheck = async () => (await api.get('/health')).data

export const getDiscoveryOverview = async () => (await api.get('/discovery/overview')).data
export const addDiscoverySource = async (source) => (await api.post('/discovery/sources', source)).data
export const deleteDiscoverySource = async (id) => (await api.delete(`/discovery/sources/${id}`)).data
export const addWatchlistItem = async (item) => (await api.post('/discovery/watchlist', item)).data
export const deleteWatchlistItem = async (id) => (await api.delete(`/discovery/watchlist/${id}`)).data
export const runDiscovery = async () => (await api.post('/discovery/run')).data
