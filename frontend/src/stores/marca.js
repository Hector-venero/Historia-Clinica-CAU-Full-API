import { defineStore } from 'pinia';
import api from '@/api/axios';

/**
 * Marca del consultorio: nombre y logo.
 *
 * Estaban escritos en el código ("CAU UNSAM", el logo de la UNSAM), lo que con
 * varios consultorios en la misma aplicación significaría que todos se ven como
 * el primero. Ahora salen del backend, que los resuelve según el subdominio.
 *
 * Se pide a `/api/publico/marca`, **sin sesión**: la pantalla de entrada tiene
 * que mostrar el nombre del consultorio antes de que nadie se autentique. Ese
 * endpoint devuelve solo nombre y logo, nada del plan ni del estado.
 *
 * Los valores por defecto son los del CAU: si la petición falla, la aplicación
 * sigue viéndose como siempre en vez de quedar sin encabezado.
 */
export const useMarcaStore = defineStore('marca', {
    state: () => ({
        nombre: 'Centro Asistencial Universitario UNSAM',
        nombreCorto: 'CAU UNSAM',
        logo: null,
        cargada: false
    }),

    actions: {
        async cargar() {
            // Una sola vez por carga de página: no cambia mientras se navega.
            if (this.cargada) return;

            try {
                const { data } = await api.get('/publico/marca');
                if (data?.nombre) this.nombre = data.nombre;
                if (data?.nombre_corto) this.nombreCorto = data.nombre_corto;
                this.logo = data?.logo || null;
            } catch {
                // Sin marca del servidor se usan los valores por defecto. No es
                // motivo para dejar la pantalla en blanco.
            } finally {
                this.cargada = true;
            }
        }
    }
});
