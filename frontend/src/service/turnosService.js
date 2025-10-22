// src/service/turnosService.js
import axios from 'axios';

export default {
    listar() {
        return axios.get('/api/turnos', { withCredentials: true });
    },
    crear(data) {
        return axios.post('/api/turnos', data, { withCredentials: true });
    },
    actualizar(id, data) {
        return axios.put(`/api/turnos/${id}`, data, { withCredentials: true });
    },
    eliminar(id) {
        return axios.delete(`/api/turnos/${id}`, { withCredentials: true });
    }
};
