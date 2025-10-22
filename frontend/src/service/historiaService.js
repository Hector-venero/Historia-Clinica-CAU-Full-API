// src/service/historiaService.js
import axios from 'axios';

export default {
    buscarPacientes(query) {
        return axios.get(`/api/pacientes/buscar?q=${encodeURIComponent(query)}`, { withCredentials: true });
    },
    getHistorias(pacienteId) {
        return axios.get(`/api/pacientes/${pacienteId}/historias`, { withCredentials: true });
    },
    crearHistoria(pacienteId, data) {
        return axios.post(`/api/pacientes/${pacienteId}/historias`, data, { withCredentials: true });
    },
    descargarPDF(pacienteId) {
        return axios.get(`/api/pacientes/${pacienteId}/historias/pdf`, {
            responseType: 'blob',
            withCredentials: true,
        });
    }
};
