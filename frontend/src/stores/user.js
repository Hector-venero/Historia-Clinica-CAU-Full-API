// src/stores/user.js
import { defineStore } from 'pinia'
import axios from 'axios'

export const useUserStore = defineStore('user', {
  state: () => ({
    id: null,
    nombre: '',
    rol: '',
    email: ''
  }),

  actions: {
    setUser(data) {
      this.id = data.id
      this.nombre = data.nombre
      this.rol = data.rol?.toLowerCase().trim() || ''
      this.email = data.email
      console.log('✅ Rol guardado en store:', this.rol)
    },
    async fetchUser() {
      try {
        const res = await axios.get('/api/user', { withCredentials: true })
        this.setUser(res.data)
      } catch (err) {
        console.error('Error cargando usuario:', err)
      }
    },
    logout() {
      this.id = null
      this.nombre = ''
      this.rol = ''
      this.email = ''
    }
  },

  getters: {
    isDirector: (state) => state.rol === 'director',
    isProfesional: (state) => state.rol === 'profesional',
    isAdministrativo: (state) => state.rol === 'administrativo'
  }
})
