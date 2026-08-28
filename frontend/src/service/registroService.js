import api from '@/api/axios';

/**
 * Alta autoservicio. Vive en el dominio raíz, no en el de un consultorio:
 * quien se registra todavía no tiene subdominio.
 */
export default {
    /** Consulta en vivo mientras se escribe. Devuelve la dirección normalizada. */
    disponible(slug) {
        return api.get('/registro/disponible', { params: { slug } });
    },

    /** Guarda la intención y dispara el correo. No crea ninguna base todavía. */
    registrar(datos) {
        return api.post('/registro', datos);
    },

    /** Confirma el correo y crea el consultorio. Tarda unos segundos. */
    verificar(token) {
        return api.post(`/registro/verificar/${token}`);
    },

    /** Para la pantalla de "preparando tu sistema". */
    estado(token) {
        return api.get(`/registro/estado/${token}`);
    }
};
