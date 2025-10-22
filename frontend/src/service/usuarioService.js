// src/service/usuarioService.js
import axios from 'axios'

const API_URL = '/api/usuarios'

export default {
  getUsuarios(params = {}) {
    return axios.get(API_URL, { params, withCredentials: true })
  },
  getUsuario(id) {
    return axios.get(`${API_URL}/${id}`, { withCredentials: true })
  },
  createUsuario({ nombre, username, email, password, rol, especialidad }) {
    return axios.post(API_URL,
      { nombre, username, email, password, rol, especialidad },
      { withCredentials: true }
    )
  },
  updateUsuario(id, data) {
    return axios.put(`${API_URL}/${id}`, data, { withCredentials: true })
  },
  deleteUsuario(id) {
    return axios.delete(`${API_URL}/${id}`, { withCredentials: true })
  },
  activarUsuario(id) {
    return axios.put(`${API_URL}/${id}/activar`, {}, { withCredentials: true })
  }
}
