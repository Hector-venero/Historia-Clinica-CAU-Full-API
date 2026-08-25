// src/service/usuarioService.js
import api from '@/api/axios';

const API_URL = '/usuarios'; // api ya agrega /api

export default {
    getUsuarios(params = {}) {
        return api.get(API_URL, { params, withCredentials: true });
    },

    getUsuario(id) {
        return api.get(`${API_URL}/${id}`, { withCredentials: true });
    },

    // Se manda el objeto completo y no una lista fija de campos: al
    // desestructurar, cualquier campo nuevo del formulario (matrícula, lugar de
    // atención) se perdía en silencio antes de llegar al backend.
    createUsuario(data) {
        return api.post(API_URL, data, { withCredentials: true });
    },

    updateUsuario(id, data) {
        return api.put(`${API_URL}/${id}`, data, { withCredentials: true });
    },

    deleteUsuario(id) {
        return api.delete(`${API_URL}/${id}`, { withCredentials: true });
    },

    activarUsuario(id) {
        return api.put(`${API_URL}/${id}/activar`, {}, { withCredentials: true });
    },

    actualizarDuracion(id, duracion_turno) {
        return api.patch(`${API_URL}/${id}/duracion`, { duracion_turno }, { withCredentials: true });
    }
};
