// src/stores/user.js
import { defineStore } from "pinia";
import { emit } from "@/utils/eventBus";
import usuarioService from "@/service/usuarioService";

export const useUserStore = defineStore("user", {
  state: () => ({
    id: null,
    nombre: "",
    username: "",
    rol: "",
    email: "",
    duracion_turno: 20,
    foto: null
  }),

  actions: {
    setUser(data) {
      this.id = data.id ?? null;
      this.nombre = data.nombre ?? "";
      this.username = data.username ?? "";
      this.rol = data.rol?.toLowerCase().trim() || "";
      this.email = data.email ?? "";
      this.duracion_turno = data.duracion_turno ?? this.duracion_turno;
      this.foto = data.foto ?? null;

      console.log("✅ Usuario cargado:", this.$state);

      emit("user:updated", { ...this.$state });
    },

    async fetchUser() {
      try {
        const res = await usuarioService.getUsuario("me"); // o /user si es tu endpoint
        this.setUser(res.data);
        return res.data;
      } catch (err) {
        console.error("❌ Error cargando usuario:", err);
        this.logout();
        throw err;
      }
    },

    async actualizarDuracion(nuevaDuracion) {
      try {
        await usuarioService.actualizarDuracion(this.id, nuevaDuracion);
        this.duracion_turno = nuevaDuracion;
        console.log(`✅ Duración de turno actualizada a ${nuevaDuracion} min`);
      } catch (err) {
        console.error("❌ Error actualizando duración de turno:", err);
        throw err;
      }
    },

    logout() {
      this.$reset();
      emit("user:loggedOut");
    }
  },

  getters: {
    isDirector: (state) => state.rol === "director",
    isProfesional: (state) => state.rol === "profesional",
    isAdministrativo: (state) => state.rol === "administrativo"
  }
});
