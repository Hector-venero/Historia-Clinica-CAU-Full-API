// src/service/servicioService.js
//
// Servicios (prestaciones) del consultorio: consulta, control, urgencia, cada
// uno con su duración y su precio.
//
// Son opcionales. Un consultorio que no cargue ninguno agenda como siempre, con
// la duración única del profesional, y las pantallas tienen que seguir
// funcionando con la lista vacía.
import api from '@/api/axios';

const API_URL = '/servicios'; // api ya agrega /api

export default {
    // Sin `usuarioId`, el catálogo completo (la pantalla de configurar).
    // Con `usuarioId`, solo los que ese profesional puede dar: los suyos y los
    // del consultorio. Es lo que necesitan las pantallas que agendan.
    listar({ usuarioId = null, soloActivos = false } = {}) {
        const params = {};
        if (usuarioId) params.usuario_id = usuarioId;
        if (soloActivos) params.activos = 1;
        return api.get(API_URL, { params, withCredentials: true });
    },

    crear(data) {
        return api.post(API_URL, data, { withCredentials: true });
    },

    actualizar(id, data) {
        return api.put(`${API_URL}/${id}`, data, { withCredentials: true });
    },

    // Da de baja, no borra: los turnos ya dados apuntan al servicio.
    darDeBaja(id) {
        return api.delete(`${API_URL}/${id}`, { withCredentials: true });
    }
};
