// src/stores/user.js
import { defineStore } from 'pinia';
import { emit } from '@/utils/eventBus';
import usuarioService from '@/service/usuarioService';

// La sesión NO se persiste en localStorage.
//
// Antes el rol se guardaba ahí y el guard del router lo leía de vuelta. Como
// localStorage es editable desde las devtools, cualquiera podía asignarse
// `rol: "director"` y entrar a las pantallas de administración. El backend
// igual rechazaba las operaciones (@requiere_rol), así que no era una fuga de
// datos, pero sí exponía una interfaz que no le corresponde a ese usuario.
//
// Ahora la única fuente de verdad es el backend: el guard pide /api/usuarios/me
// y el rol viene de la cookie de sesión, que es HttpOnly y no se puede falsear
// desde el navegador.
// Se enumeran una sola vez para que el estado inicial y setUser no puedan
// quedar desalineados: agregar un campo en un solo lado dejaba a la pantalla de
// recetas leyendo undefined sin ningún error visible.
const CAMPOS_PROFESIONALES = [
    'apellido',
    'dni',
    'sexo',
    'telefono',
    'profesion',
    'especialidad',
    'matricula_tipo',
    'matricula_numero',
    'matricula_provincia',
    'lugar_atencion_nombre',
    'lugar_atencion_direccion',
    'lugar_atencion_contacto',
    'lugar_atencion_email'
];

export const useUserStore = defineStore('user', {
    state: () => ({
        id: null,
        nombre: '',
        username: '',
        rol: '',
        email: '',
        duracion_turno: 20,
        foto: null,
        fotoVersion: Date.now(),
        // Identidad profesional. La necesita la pantalla de recetas para armar
        // el bloque `medico` y el `lugarAtencion` sin volver a pedir el perfil.
        // /api/usuarios/me ya los devolvía; setUser los descartaba, y sin ellos
        // el formulario de emisión nunca se daba por completo.
        apellido: '',
        dni: '',
        sexo: '',
        telefono: '',
        profesion: '',
        especialidad: '',
        matricula_tipo: '',
        matricula_numero: '',
        matricula_provincia: '',
        lugar_atencion_nombre: '',
        lugar_atencion_direccion: '',
        lugar_atencion_contacto: '',
        lugar_atencion_email: '',
        // Evita el rebote login -> dashboard mientras se está cerrando sesión.
        loggingOut: false
    }),

    actions: {
        setUser(data) {
            this.id = data.id ?? null;
            this.nombre = data.nombre ?? '';
            this.username = data.username ?? '';
            this.rol = data.rol?.toLowerCase().trim() || ''; // Normalizamos rol
            this.email = data.email ?? '';
            this.duracion_turno = data.duracion_turno ?? this.duracion_turno;
            this.foto = data.foto ?? null;

            // Se copian con '' y no con null para que los v-model de los
            // formularios no arranquen en null y marquen el campo como sucio.
            for (const campo of CAMPOS_PROFESIONALES) {
                this[campo] = data[campo] ?? '';
            }

            this.loggingOut = false;

            emit('user:updated', { ...this.$state });
        },

        async fetchUser() {
            try {
                const res = await usuarioService.getUsuario('me');
                this.setUser(res.data);
                return res.data;
            } catch (err) {
                console.error('❌ Error cargando usuario:', err);
                throw err;
            }
        },

        recargarImagen() {
            this.fotoVersion = Date.now();
        },

        async actualizarDuracion(nuevaDuracion) {
            try {
                await usuarioService.actualizarDuracion(this.id, nuevaDuracion);
                this.duracion_turno = nuevaDuracion;
            } catch (err) {
                console.error('❌ Error actualizando duración:', err);
                throw err;
            }
        },

        // Se llama ANTES de disparar el logout en el backend: sin esta marca, el
        // guard ve que el store todavía tiene usuario y rebota de vuelta al
        // dashboard en lugar de dejar salir.
        startLogout() {
            this.loggingOut = true;
        },

        logout() {
            this.$reset();
            emit('user:loggedOut');
        }
    },

    getters: {
        isDirector: (state) => state.rol === 'director',
        isProfesional: (state) => state.rol === 'profesional',
        isAdministrativo: (state) => state.rol === 'administrativo'
    }
});
