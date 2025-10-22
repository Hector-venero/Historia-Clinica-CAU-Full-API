// src/service/ausenciasService.js
import axios from 'axios';

export default {
    listar() {
        return axios.get('/api/ausencias', { withCredentials: true });
    },
    crear(data) {
        return axios.post('/api/ausencias', data, { withCredentials: true });
    },
    eliminar(id) {
        return axios.delete(`/api/ausencias/${id}`, { withCredentials: true });
    }
};
