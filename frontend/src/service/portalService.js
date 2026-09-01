import api from '@/api/axios';

/**
 * Portal del paciente. Vive en el subdominio `mi.<dominio>`, no en el de un
 * consultorio: un paciente no pertenece a ninguno, y lo que se busca es que vea
 * junto lo que le mandaron varios.
 */
export default {
    registrar(datos) {
        return api.post('/portal/registro', datos);
    },

    /** Confirma el correo, crea la cuenta e inicia sesión en un solo paso. */
    verificar(token) {
        return api.post(`/portal/verificar/${token}`);
    },

    login(email, password) {
        return api.post('/portal/login', { email, password });
    },

    logout() {
        return api.post('/portal/logout');
    },

    me() {
        return api.get('/portal/me');
    },

    actualizarPerfil(datos) {
        return api.post('/portal/perfil', datos);
    },

    /** Todo lo que le enviaron, de todos los consultorios. */
    documentos() {
        return api.get('/portal/documentos');
    },

    sinLeer() {
        return api.get('/portal/documentos/sin_leer');
    },

    marcarLeido(id) {
        return api.post(`/portal/documentos/${id}/leer`);
    },

    /**
     * Descarga el adjunto. Va por id y no por el token del archivo: el backend
     * valida la pertenencia en el WHERE de la consulta.
     */
    descargarArchivo(id) {
        return api.get(`/portal/documentos/${id}/archivo`, { responseType: 'blob' });
    },

    // --- Turnos online ---
    //
    // El directorio y los horarios se consultan SIN sesión: alguien tiene que
    // poder ver con quién puede atenderse, y si hay lugar, antes de decidir si
    // se registra. Lo único que exige cuenta es confirmar.

    profesionales(params) {
        return api.get('/portal/profesionales', { params });
    },

    especialidades() {
        return api.get('/portal/especialidades');
    },

    /**
     * Las prestaciones del profesional, para elegir antes que el horario.
     *
     * Devuelve lista vacía si el consultorio no usa servicios, que es el caso
     * por defecto: ahí la reserva es como siempre, solo con el horario.
     */
    servicios(clienteId, usuarioId) {
        return api.get(`/portal/profesionales/${clienteId}/${usuarioId}/servicios`);
    },

    // `servicioId` cambia la grilla: los horarios se arman con la duración de
    // ese servicio. Sin él, con la del profesional.
    horarios(clienteId, usuarioId, fecha, servicioId = null) {
        return api.get(`/portal/profesionales/${clienteId}/${usuarioId}/horarios`, {
            params: { fecha, servicio_id: servicioId || undefined }
        });
    },

    /** El primer día con lugar, para no dejar a la persona probando día por día. */
    proximoDia(clienteId, usuarioId, desde, servicioId = null) {
        return api.get(`/portal/profesionales/${clienteId}/${usuarioId}/proximo-dia`, {
            params: { desde, servicio_id: servicioId || undefined }
        });
    },

    reservar(datos) {
        return api.post('/portal/reservar', datos);
    },

    /** Los turnos del paciente, ya verificados contra cada consultorio. */
    misTurnos() {
        return api.get('/portal/mis-turnos');
    },

    cancelarTurno(reservaId) {
        return api.delete(`/portal/mis-turnos/${reservaId}`);
    },

    /**
     * Pide el enlace para restablecer la contraseña.
     *
     * Responde lo mismo exista o no la cuenta: el formulario es público y
     * distinguirlo dejaría averiguar quién es paciente de la plataforma.
     */
    recuperar(email) {
        return api.post('/portal/recuperar', { email });
    },

    resetear(token, password, passwordRepetida) {
        return api.post(`/portal/reset/${token}`, {
            password,
            password_repetida: passwordRepetida
        });
    }
};
