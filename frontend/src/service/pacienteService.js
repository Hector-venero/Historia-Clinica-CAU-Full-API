import axios from 'axios';

const API_URL = 'http://localhost:5000/api'; // ✅ Tu Flask corre aquí

export default {
    getPacientes() {
        return axios.get('/api/pacientes', { withCredentials: true });
    },
    crearPaciente(data) {
        return axios.post('/api/pacientes', data, { withCredentials: true });
    },
    updatePaciente(id, data) {
        return axios.put(`/api/pacientes/${id}`, data, { withCredentials: true });
    },
    getPaciente(id) {
        return axios.get(`/api/pacientes/${id}`, { withCredentials: true });
    },
    deletePaciente(id) {
        return axios.delete(`/api/pacientes/${id}`, { withCredentials: true });
    },
};
