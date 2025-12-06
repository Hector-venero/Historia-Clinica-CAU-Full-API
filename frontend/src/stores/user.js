// src/stores/user.js
import { defineStore } from 'pinia'
import axios from 'axios'
import { emit } from '@/utils/eventBus'

export const useUserStore = defineStore('user', {
  state: () => ({
    id: null,
    nombre: '',
    username: '',
    rol: '',
    email: '',
    duracion_turno: 20,
    foto: null
  }),

  actions: {
    // Guarda los datos del usuario en el store
    setUser(data) {
      this.id = data.id ?? null
      this.nombre = data.nombre ?? ''
      this.username = data.username ?? ''
      this.rol = data.rol?.toLowerCase().trim() || ''
      this.email = data.email ?? ''
      this.duracion_turno = data.duracion_turno ?? this.duracion_turno
      this.foto = data.foto ?? null

      console.log(
        '✅ Usuario cargado:',
        this.nombre,
        '| Rol:', this.rol,
        '| Foto:', this.foto,
        '| Duración turno:', this.duracion_turno
      )

      // 🔔 Notificar a toda la app
      emit('user:updated', { ...this.$state })
    },

    // Trae el usuario actual desde backend
    async fetchUser() {
      try {
        const res = await axios.get('/api/user', {
          withCredentials: true
        })
        this.setUser(res.data)
        return res.data
      } catch (err) {
        console.error('❌ Error cargando usuario:', err)
        this.logout()
        throw err
      }
    },

    // Actualiza duración del turno en backend
    async actualizarDuracion(nuevaDuracion) {
      try {
        await axios.patch(
          `/api/usuarios/${this.id}/duracion`,
          { duracion_turno: nuevaDuracion },
          { withCredentials: true }
        )

        this.duracion_turno = nuevaDuracion
        console.log(`✅ Duración de turno actualizada a ${nuevaDuracion} min`)
      } catch (err) {
        console.error('❌ Error actualizando duración de turno:', err)
        throw err
      }
    },

    logout() {
      this.id = null
      this.nombre = ''
      this.username = ''
      this.rol = ''
      this.email = ''
      this.duracion_turno = 20
      this.foto = null

      emit('user:loggedOut')
    }
  },

  getters: {
    isDirector: (state) => state.rol === 'director',
    isProfesional: (state) => state.rol === 'profesional',
    isAdministrativo: (state) => state.rol === 'administrativo'
  }
})
