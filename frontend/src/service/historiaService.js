// src/service/historiaService.js
import api from '@/api/axios';

export default {
    buscarPacientes(query) {
        return api.get(`/pacientes/buscar?q=${encodeURIComponent(query)}`, { withCredentials: true });
    },
    getHistorias(pacienteId) {
        return api.get(`/pacientes/${pacienteId}/historias`, { withCredentials: true });
    },
    crearHistoria(pacienteId, data) {
        return api.post(`/pacientes/${pacienteId}/historias`, data, { withCredentials: true });
    },
    // El backend expone /historia/pdf en singular. Acá decía /historias/pdf y
    // devolvía 404; no se notaba porque ninguna vista usaba esta función.
    descargarPDF(pacienteId) {
        return api.get(`/pacientes/${pacienteId}/historia/pdf`, {
            responseType: 'blob',
            withCredentials: true
        });
    },
    descargarEvolucionPDF(pacienteId, evolucionId) {
        return api.get(`/pacientes/${pacienteId}/evolucion/${evolucionId}/pdf`, {
            responseType: 'blob',
            withCredentials: true
        });
    }
};
