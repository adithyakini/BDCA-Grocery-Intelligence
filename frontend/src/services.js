import axios from 'axios'

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api', timeout: 15000 })
export const getDashboard = async () => (await api.get('/dashboard')).data
export const getOffers = async (params = {}) => (await api.get('/offers', { params })).data
export const reviewOffer = async (id, status, note = '') => (await api.post(`/offers/${id}/review`, { status, note })).data
export const addDemoOffer = async () => (await api.post('/offers/demo')).data
export const createOffer = async (offer) => (await api.post('/offers', offer)).data
export const healthCheck = async () => (await api.get('/health')).data
