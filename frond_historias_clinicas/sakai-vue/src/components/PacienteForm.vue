<template>
  <div class="p-4">
    <h1 class="text-2xl font-bold mb-4">Registrar Paciente</h1>
    <form @submit.prevent="registrar">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- N° de H.C. -->
        <div>
          <label class="block mb-1">Nº de H.C. <span class="text-red-500">*</span></label>
          <input v-model="paciente.nro_hc" type="text" class="p-inputtext p-component w-full h-12" />
          <span v-if="intentadoEnviar && !paciente.nro_hc" class="text-red-500 text-sm">Campo obligatorio</span>
        </div>
        <!-- Nombre -->
        <div>
          <label class="block mb-1">Nombre <span class="text-red-500">*</span></label>
          <input v-model="paciente.nombre" type="text" class="p-inputtext p-component w-full h-12" />
          <span v-if="intentadoEnviar && !paciente.nombre" class="text-red-500 text-sm">Campo obligatorio</span>
        </div>
        <!-- Apellido -->
        <div>
          <label class="block mb-1">Apellido <span class="text-red-500">*</span></label>
          <input v-model="paciente.apellido" type="text" class="p-inputtext p-component w-full h-12" />
          <span v-if="intentadoEnviar && !paciente.apellido" class="text-red-500 text-sm">Campo obligatorio</span>
        </div>
        <!-- DNI -->
        <div>
          <label class="block mb-1">N° de Documento <span class="text-red-500">*</span></label>
          <input v-model="paciente.dni" type="text" class="p-inputtext p-component w-full h-12" />
          <span v-if="intentadoEnviar && !paciente.dni" class="text-red-500 text-sm">Campo obligatorio</span>
        </div>
        <!-- Fecha de nacimiento -->
        <div>
          <label class="block mb-1">Fecha de Nacimiento <span class="text-red-500">*</span></label>
          <input v-model="paciente.fecha_nacimiento" type="date" class="p-inputtext p-component w-full h-12" />
          <span v-if="intentadoEnviar && !paciente.fecha_nacimiento" class="text-red-500 text-sm">Campo obligatorio</span>
        </div>
        <!-- Sexo -->
        <div>
          <label class="block mb-1">Sexo <span class="text-red-500">*</span></label>
          <select v-model="paciente.sexo" class="p-inputtext p-component w-full h-12">
            <option value="">Seleccionar</option>
            <option>Femenino</option>
            <option>Masculino</option>
            <option>Otro</option>
          </select>
          <span v-if="intentadoEnviar && !paciente.sexo" class="text-red-500 text-sm">Campo obligatorio</span>
        </div>
        <!-- Ocupación -->
        <div>
          <label class="block mb-1">Ocupación</label>
          <input v-model="paciente.ocupacion" type="text" class="p-inputtext p-component w-full h-12" />
        </div>
        <!-- Nacionalidad -->
        <div>
          <label class="block mb-1">Nacionalidad</label>
          <input v-model="paciente.nacionalidad" type="text" class="p-inputtext p-component w-full h-12" />
        </div>
        <!-- Dirección -->
        <div>
          <label class="block mb-1">Dirección (Calle, CP, Ciudad)</label>
          <input v-model="paciente.direccion" type="text" class="p-inputtext p-component w-full h-12" placeholder="Ej: Savio 1683, CP 1650, San Martín" />
        </div>
        <!-- Código postal -->
        <div>
          <label class="block mb-1">Código Postal</label>
          <input v-model="paciente.codigo_postal" type="text" class="p-inputtext p-component w-full h-12" />
        </div>
        <!-- Teléfono -->
        <div>
          <label class="block mb-1">Teléfono <span class="text-red-500">*</span> o Celular</label>
          <input v-model="paciente.telefono" type="text" class="p-inputtext p-component w-full h-12" />
          <span v-if="intentadoEnviar && !paciente.telefono && !paciente.celular" class="text-red-500 text-sm">Ingresar al menos uno</span>
        </div>
        <!-- Celular -->
        <div>
          <label class="block mb-1">Celular</label>
          <input v-model="paciente.celular" type="text" class="p-inputtext p-component w-full h-12" />
        </div>
        <!-- Email -->
        <div>
          <label class="block mb-1">Mail</label>
          <input v-model="paciente.email" type="email" class="p-inputtext p-component w-full h-12" />
        </div>
        <!-- Contacto -->
        <div>
          <label class="block mb-1">Contacto</label>
          <input v-model="paciente.contacto" type="text" class="p-inputtext p-component w-full h-12" placeholder="Ej: Hija Natalia" />
        </div>
        <!-- Cobertura -->
        <div>
          <label class="block mb-1">Cobertura</label>
          <input v-model="paciente.cobertura" type="text" class="p-inputtext p-component w-full h-12" />
        </div>
        <!-- Certificado discapacidad -->
        <div>
          <label class="block mb-1">Certificado de Discapacidad</label>
          <select v-model="paciente.cert_discapacidad" class="p-inputtext p-component w-full h-12">
            <option value="">Seleccionar</option>
            <option value="Si">Si</option>
            <option value="No">No</option>
          </select>
        </div>
        <!-- Nº Certificado -->
        <div>
          <label class="block mb-1">Nº Certificado</label>
          <input v-model="paciente.nro_certificado" type="text" class="p-inputtext p-component w-full h-12" />
        </div>
        <!-- Derivado por -->
        <div>
          <label class="block mb-1">Derivado por</label>
          <input v-model="paciente.derivado_por" type="text" class="p-inputtext p-component w-full h-12" />
        </div>
        <!-- Diagnóstico -->
        <div>
          <label class="block mb-1">Diagnóstico</label>
          <input v-model="paciente.diagnostico" type="text" class="p-inputtext p-component w-full h-12" />
        </div>
        <!-- Motivo derivación -->
        <div>
          <label class="block mb-1">Motivo de derivación</label>
          <input v-model="paciente.motivo_derivacion" type="text" class="p-inputtext p-component w-full h-12" />
        </div>
        <!-- Médico cabecera -->
        <div>
          <label class="block mb-1">Médico de cabecera</label>
          <input v-model="paciente.medico_cabecera" type="text" class="p-inputtext p-component w-full h-12" />
        </div>
      </div>

      <!-- Comentarios -->
      <div class="mt-6">
        <label class="block mb-1">Comentarios</label>
        <textarea v-model="paciente.comentarios" rows="4" class="p-inputtext p-component w-full"></textarea>
      </div>

      <button type="submit" class="p-button p-component mt-6 bg-green-500 text-white">Registrar</button>
    </form>

    <!-- Mensaje -->
    <p v-if="mensaje" :class="tipoMensaje === 'success' ? 'text-green-600' : 'text-red-600'" class="mt-4">
      {{ mensaje }}
    </p>
  </div>
</template>

<script setup>
import pacienteService from '@/service/pacienteService'
import { ref } from 'vue'

const paciente = ref({
  nro_hc: '',
  nombre: '',
  apellido: '',
  dni: '',
  fecha_nacimiento: '',
  sexo: '',
  nacionalidad: '',
  ocupacion: '',
  direccion: '',
  codigo_postal: '',
  telefono: '',
  celular: '',
  email: '',
  contacto: '',
  cobertura: '',
  cert_discapacidad: '',
  nro_certificado: '',
  derivado_por: '',
  diagnostico: '',
  motivo_derivacion: '',
  medico_cabecera: '',
  comentarios: ''
})

const mensaje = ref('')
const tipoMensaje = ref('')
const intentadoEnviar = ref(false)

const registrar = async () => {
  intentadoEnviar.value = true

  if (!paciente.value.nro_hc || !paciente.value.nombre || !paciente.value.apellido ||
      !paciente.value.dni || !paciente.value.fecha_nacimiento || !paciente.value.sexo ||
      (!paciente.value.telefono && !paciente.value.celular)) {
    mensaje.value = '⚠️ Completá todos los campos obligatorios.'
    tipoMensaje.value = 'error'
    return
  }

  try {
    const formData = new FormData()
    for (const key in paciente.value) {
      formData.append(key, paciente.value[key])
    }

    const response = await pacienteService.crearPaciente(formData)

    if (response.data && response.data.message) {
      mensaje.value = response.data.message
      tipoMensaje.value = 'success'
      paciente.value = {
        nro_hc: '',
        nombre: '',
        apellido: '',
        dni: '',
        fecha_nacimiento: '',
        sexo: '',
        nacionalidad: '',
        ocupacion: '',
        direccion: '',
        codigo_postal: '',
        telefono: '',
        celular: '',
        email: '',
        contacto: '',
        cobertura: '',
        cert_discapacidad: '',
        nro_certificado: '',
        derivado_por: '',
        diagnostico: '',
        motivo_derivacion: '',
        medico_cabecera: '',
        comentarios: ''
      }
      intentadoEnviar.value = false
    } else if (response.data && response.data.error) {
      mensaje.value = response.data.error
      tipoMensaje.value = 'error'
    } else {
      mensaje.value = '⚠️ Error inesperado al registrar paciente.'
      tipoMensaje.value = 'error'
    }
  } catch (error) {
    console.error(error)
    mensaje.value = '❌ Error de red o servidor.'
    tipoMensaje.value = 'error'
  }
}
</script>

<style scoped></style>
