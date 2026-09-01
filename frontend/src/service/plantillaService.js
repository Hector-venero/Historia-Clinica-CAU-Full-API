// src/service/plantillaService.js
//
// Plantillas de texto clínico: lo que se repite al escribir una evolución.
//
// La plantilla es un **punto de partida**, no el texto final: se inserta en el
// formulario y se edita antes de guardar. Nunca se escribe sola en una historia.
import api from '@/api/axios';

const API_URL = '/plantillas'; // api ya agrega /api

export default {
    // Sin `todas`, solo las activas que puede usar quien pregunta (las suyas y
    // las del consultorio). Es lo que necesita la pantalla de escribir.
    // Con `todas`, el catálogo completo, para administrarlas.
    listar({ campo = null, todas = false } = {}) {
        const params = {};
        if (campo) params.campo = campo;
        if (todas) params.todas = 1;
        return api.get(API_URL, { params, withCredentials: true });
    },

    crear(data) {
        return api.post(API_URL, data, { withCredentials: true });
    },

    actualizar(id, data) {
        return api.put(`${API_URL}/${id}`, data, { withCredentials: true });
    },

    // Se borra de verdad: lo que queda en la evolución es el texto copiado, no
    // un puntero, así que borrarla no deja huérfano a ningún registro clínico.
    borrar(id) {
        return api.delete(`${API_URL}/${id}`, { withCredentials: true });
    }
};
