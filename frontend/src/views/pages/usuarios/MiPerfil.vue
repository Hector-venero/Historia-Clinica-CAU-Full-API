<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { useUserStore } from '@/stores/user'
import { buildFotoURL } from '@/utils/fotoUrl.js'

const userStore = useUserStore()

// Campos formulario
const nombre = ref('')
const email = ref('')
const fotoActual = ref('')
const archivoFoto = ref(null)
const mensaje = ref('')

// Cargar datos iniciales
onMounted(() => {
  nombre.value = userStore.nombre
  email.value = userStore.email

  fotoActual.value = buildFotoURL(userStore.foto) || ''
})

/* Manejar selección de foto */
const onFileChange = (e) => {
  const file = e.target.files[0]
  if (!file) {
    archivoFoto.value = null
    return
  }

  archivoFoto.value = file
  fotoActual.value = URL.createObjectURL(file)
}

/* Guardar perfil */
const actualizarPerfil = async () => {
  const form = new FormData()
  form.append('nombre', nombre.value)
  form.append('email', email.value)

  if (archivoFoto.value) {
    form.append('foto', archivoFoto.value)
  }

  await axios.post('/api/usuario/perfil', form, {
    withCredentials: true,
    headers: { 'Content-Type': 'multipart/form-data' }
  })

  mensaje.value = 'Perfil actualizado correctamente.'

  await userStore.fetchUser()

  fotoActual.value = buildFotoURL(userStore.foto) || ''
}

/* ELIMINAR FOTO */
const eliminarFoto = async () => {
  await axios.delete('/api/usuario/foto', {
    withCredentials: true
  })

  await userStore.fetchUser()

  fotoActual.value = ''
  archivoFoto.value = null
  mensaje.value = 'Foto eliminada.'
}
</script>

<template>
  <div class="max-w-lg mx-auto bg-white p-6 rounded-xl shadow">

    <h1 class="text-2xl font-bold mb-6">Editar mi Perfil</h1>

    <label class="block mb-2 font-semibold">Nombre</label>
    <input v-model="nombre" class="w-full p-2 border rounded mb-4"/>

    <label class="block mb-2 font-semibold">Email</label>
    <input v-model="email" class="w-full p-2 border rounded mb-4"/>

    <label class="block mb-2 font-semibold">Foto de perfil</label>

    <div class="mb-3" v-if="fotoActual">
      <img
        :src="fotoActual"
        class="w-24 h-24 rounded-full object-cover border"
        alt="Foto de perfil"
      />
    </div>

    <input
      type="file"
      name="foto"
      accept="image/*"
      @change="onFileChange"
    />

    <div class="flex gap-3 mt-4">
      <button
        class="bg-blue-600 text-white px-4 py-2 rounded-lg"
        @click="actualizarPerfil"
      >
        Guardar cambios
      </button>

      <button
        v-if="fotoActual"
        class="bg-red-600 text-white px-4 py-2 rounded-lg"
        @click="eliminarFoto"
      >
        Eliminar foto
      </button>
    </div>

    <p v-if="mensaje" class="mt-4 text-green-600">{{ mensaje }}</p>
  </div>
</template>
