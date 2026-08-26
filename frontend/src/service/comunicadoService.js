import api from '@/api/axios';

export default {
    listar() {
        return api.get('/comunicados', { withCredentials: true });
    },
    crear(data) {
        return api.post('/comunicados', data, { withCredentials: true });
    },
    eliminar(id) {
        return api.delete(`/comunicados/${id}`, { withCredentials: true });
    },
    // Solo el número, para el globo de la campana: lo pide cada carga de la
    // barra superior y no necesita traerse los comunicados enteros.
    contarNoLeidos() {
        return api.get('/comunicados/no_leidos', { withCredentials: true });
    },
    marcarLeido(id) {
        return api.post(`/comunicados/${id}/leer`, {}, { withCredentials: true });
    },
    marcarTodosLeidos() {
        return api.post('/comunicados/leer_todos', {}, { withCredentials: true });
    }
};
