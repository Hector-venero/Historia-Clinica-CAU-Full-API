import api from '@/api/axios';

export default {
    config() {
        return api.get('/recetas/config', { withCredentials: true });
    },
    getFinanciadores() {
        return api.get('/recetas/financiadores', { withCredentials: true });
    },
    buscarMedicamentos(params) {
        return api.get('/recetas/medicamentos', { params, withCredentials: true });
    },
    buscarDiagnosticos(q) {
        return api.get('/recetas/diagnosticos', { params: { q }, withCredentials: true });
    },
    emitir(payload) {
        return api.post('/recetas', payload, { withCredentials: true });
    },
    // Acciones posteriores a la emision. Estaban en la pantalla anterior y el
    // backend las expone desde siempre; sin ellas una receta emitida por error
    // no se podia anular desde la interfaz.
    enviarMail(payload) {
        return api.post('/recetas/enviar_mail_manual', payload, { withCredentials: true });
    },
    anular(hashReceta) {
        return api.delete(`/recetas/anular/${hashReceta}`, { withCredentials: true });
    }
};
