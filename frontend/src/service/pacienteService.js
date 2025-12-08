import api from "@/api/axios";

const API_URL = 'http://localhost:5000/api'; // ✅ Tu Flask corre aquí

export default {
    getPacientes() {
        return api.get('/pacientes', { withCredentials: true });
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
    },
};
