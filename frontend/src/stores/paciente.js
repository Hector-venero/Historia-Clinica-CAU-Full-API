import { defineStore } from 'pinia';
import portalService from '@/service/portalService';

/**
 * La sesión del paciente en el portal.
 *
 * Es un store aparte del de `user` a propósito: son dos poblaciones de usuarios
 * distintas sobre la misma aplicación. Mezclarlas en un solo store haría que el
 * guard del router no supiera cuál de las dos está mirando, que es exactamente
 * el error que en el backend dejaba a un paciente leer el listado de pacientes
 * de una clínica.
 *
 * Igual que el de `user`, no se persiste en `localStorage`: la fuente de verdad
 * es la cookie de sesión, que es HttpOnly.
 */
export const usePacienteStore = defineStore('paciente', {
    state: () => ({
        id: null,
        nombre: '',
        apellido: '',
        email: '',
        telefono: '',
        tipoDocumento: '',
        numeroDocumento: '',
        cobertura: '',
        planCobertura: '',
        nroAfiliado: '',
        fechaNacimiento: '',
        sexo: '',
        // Preferencias de aviso. Vienen en true: nadie se queda sin enterarse de
        // un estudio por un cambio que no pidio.
        avisarDocumentos: true,
        avisarTurnos: true,
        // Evita el rebote login -> buzón mientras se está cerrando sesión.
        cerrandoSesion: false
    }),

    getters: {
        autenticado: (state) => state.id !== null,
        nombreCompleto: (state) => `${state.nombre} ${state.apellido}`.trim()
    },

    actions: {
        setPaciente(data) {
            this.id = data.id ?? null;
            this.nombre = data.nombre ?? '';
            this.apellido = data.apellido ?? '';
            this.email = data.email ?? '';
            this.telefono = data.telefono ?? '';
            this.tipoDocumento = data.tipo_documento ?? '';
            this.numeroDocumento = data.numero_documento ?? '';
            this.cobertura = data.cobertura ?? '';
            this.planCobertura = data.plan_cobertura ?? '';
            this.nroAfiliado = data.nro_afiliado ?? '';
            this.fechaNacimiento = data.fecha_nacimiento ?? '';
            this.sexo = data.sexo ?? '';
            this.avisarDocumentos = data.avisar_documentos ?? true;
            this.avisarTurnos = data.avisar_turnos ?? true;
            this.cerrandoSesion = false;
        },

        async cargar() {
            const { data } = await portalService.me();
            this.setPaciente(data);
            return data;
        },

        async login(email, password) {
            const { data } = await portalService.login(email, password);
            this.setPaciente(data.paciente);
            return data.paciente;
        },

        // Se marca ANTES de disparar el logout: sin esto el guard ve que el
        // store todavía tiene paciente y rebota de vuelta al buzón.
        iniciarCierre() {
            this.cerrandoSesion = true;
        },

        async logout() {
            this.iniciarCierre();
            try {
                await portalService.logout();
            } finally {
                this.$reset();
            }
        }
    }
});
