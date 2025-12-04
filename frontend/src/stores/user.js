// src/stores/user.js
import { defineStore } from 'pinia'
import axios from 'axios'

export const useUserStore = defineStore('user', {
  state: () => ({
    id: null,
    nombre: '',
    rol: '',
    email: '',
    duracion_turno: 20 // valor por defecto si backend no devuelve nada
  }),

  actions: {
    // Guarda los datos del usuario en el store
    setUser(data) {
      this.id = data.id
      this.nombre = data.nombre
      this.rol = data.rol?.toLowerCase().trim() || ''
      this.email = data.email
      this.duracion_turno = data.duracion_turno ?? this.duracion_turno

      console.log('✅ Usuario cargado. Rol:', this.rol, '| Duración:', this.duracion_turno)
    },

    // Trae el usuario logueado desde /api/user
    async fetchUser() {
      try {
        const res = await axios.get('/api/user', { withCredentials: true })
        this.setUser(res.data)
      } catch (err) {
        console.error('❌ Error cargando usuario:', err)
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
      this.rol = ''
      this.email = ''
      this.duracion_turno = 20
    }
  },

  getters: {
    isDirector: (state) => state.rol === 'director',
    isProfesional: (state) => state.rol === 'profesional',
    isAdministrativo: (state) => state.rol === 'administrativo'
  }
})
