import api from '@/api/axios';

// Nota: no declarar acá una URL absoluta. Todas las llamadas van por la
// instancia `api`, que resuelve la base según el entorno; una constante con
// http://localhost:5000 sugiere lo contrario y no funciona fuera de desarrollo.

export default {
    getPacientes() {
        return api.get('/pacientes', { withCredentials: true });
    },
    getProximoNroHc() {
        return api.get('/pacientes/proximo-nro-hc', { withCredentials: true });
    },
    crearPaciente(data) {
        return api.post('/pacientes', data, { withCredentials: true });
    },
    updatePaciente(id, data) {
        return api.put(`/pacientes/${id}`, data, { withCredentials: true });
    },
    getPaciente(id) {
        return api.get(`/pacientes/${id}`, { withCredentials: true });
    },
    deletePaciente(id) {
        return api.delete(`/pacientes/${id}`, { withCredentials: true });
    }
};
