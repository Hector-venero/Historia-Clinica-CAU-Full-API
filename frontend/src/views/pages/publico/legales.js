/**
 * Términos y política de privacidad.
 *
 * ⚠️ **ESTO ES UN BORRADOR Y NO ESTÁ PUBLICADO.** `PUBLICADO` viene en `false`,
 * y mientras siga así el pie del sitio no los enlaza y los registros no piden
 * aceptarlos: enlazar a un texto legal sin revisar es peor que no tenerlo.
 *
 * Está escrito por quien programó el sistema, no por quien sabe de derecho.
 * Sirve para dos cosas concretas y para nada más:
 *
 *   1. Que la maquinaria quede construida y probada — la casilla, la validación
 *      en el servidor y el registro de qué versión aceptó cada uno.
 *   2. Que quien lo redacte de verdad arranque de algo que ya describe **lo que
 *      el sistema hace realmente**, en vez de una plantilla genérica de
 *      internet. Cada dato que se nombra acá se guarda de verdad, y está dicho
 *      dónde.
 *
 * Alojar datos de salud de terceros cae bajo la **Ley 25.326**, que los trata
 * como datos sensibles. Eso no se resuelve leyendo: hace falta que lo revise
 * alguien que sepa, antes del primer usuario real.
 *
 * Para publicar: revisar los textos, subir `VERSION` si cambiaron, y poner
 * `PUBLICADO` en `true`.
 */

export const PUBLICADO = false;

// Cambiar esto cada vez que cambie el texto. Es lo que se guarda junto al
// consentimiento de cada persona: sin la versión, el dato no sirve para nada.
export const VERSION = '0.1-borrador';

export const ACTUALIZADO = '2026-09-02';

/** Quién responde por los datos. Lo tiene que completar Hector. */
export const RESPONSABLE = {
    nombre: 'Ficha Salud',
    correo: 'hola@fichasalud.com.ar',
    // Domicilio y CUIT hacen falta para la inscripción del registro de bases de
    // datos ante la Agencia de Acceso a la Información Pública.
    domicilio: null,
    cuit: null
};

export const TERMINOS = {
    titulo: 'Términos y condiciones',
    bajada: 'Las reglas de uso de Ficha Salud, para consultorios y para pacientes.',
    secciones: [
        {
            titulo: 'Qué es Ficha Salud',
            cuerpo: [
                'Ficha Salud es un sistema de gestión para consultorios y centros médicos: agenda de turnos, historia clínica, recetas electrónicas y un portal donde el paciente recibe lo que sus profesionales le envían.',
                'El servicio se presta tal como está disponible. No reemplaza el criterio profesional ni la obligación de llevar la historia clínica según la normativa aplicable.'
            ]
        },
        {
            titulo: 'Dos tipos de cuenta, con reglas distintas',
            cuerpo: [
                'La cuenta de un **consultorio** la contrata un profesional o una institución, y desde ella se cargan datos de sus pacientes. Quien la contrata es responsable de lo que carga y de quién accede.',
                'La cuenta de un **paciente** es gratuita y personal. Le sirve para ver lo que le enviaron y para sacar turnos.'
            ]
        },
        {
            titulo: 'La historia clínica es del paciente',
            cuerpo: [
                'Los datos clínicos cargados por un consultorio le pertenecen a ese consultorio y a sus pacientes, no a Ficha Salud.',
                'Se pueden exportar en cualquier momento, incluso con la suscripción suspendida por falta de pago. Suspender una cuenta no bloquea la exportación.'
            ]
        },
        {
            titulo: 'Baja y conservación',
            cuerpo: [
                'La suscripción es mes a mes y se da de baja cuando se quiera, sin permanencia.',
                'Tras la baja, los datos se conservan un tiempo para permitir la exportación y después se eliminan. **Ese plazo hay que definirlo**, teniendo en cuenta que la normativa argentina exige conservar la historia clínica durante años.'
            ]
        },
        {
            titulo: 'Disponibilidad',
            cuerpo: [
                'Se procura la continuidad del servicio, pero **no se garantiza que esté disponible sin interrupciones**. Puede haber cortes por mantenimiento o por fallas de terceros.',
                'Esto importa: si el sistema no está disponible, el consultorio tiene que poder atender igual.'
            ]
        }
    ]
};

export const PRIVACIDAD = {
    titulo: 'Política de privacidad',
    bajada: 'Qué datos se guardan, para qué, y qué se puede hacer con ellos.',
    secciones: [
        {
            titulo: 'Datos de salud: son datos sensibles',
            cuerpo: [
                'La historia clínica, las recetas y los estudios son **datos sensibles** según la Ley 25.326. Se tratan con esa condición: se usan para prestar el servicio y para nada más.',
                'No se venden, no se ceden con fines comerciales y no se usan para publicidad.'
            ]
        },
        {
            titulo: 'Qué se guarda de un paciente',
            cuerpo: [
                'Nombre y apellido, tipo y número de documento, correo, teléfono y datos de cobertura. El documento es la llave con la que dos consultorios distintos le envían algo a la misma persona.',
                'En el buzón se guardan copias de lo que un profesional decidió enviarle. Son copias a propósito: si ese consultorio deja de usar el sistema, la persona no pierde sus estudios.'
            ]
        },
        {
            titulo: 'Cómo se separan los datos de cada consultorio',
            cuerpo: [
                'Cada consultorio tiene **su propia base de datos**, con su propio usuario, no una tabla compartida con un filtro. Un consultorio no puede ver los pacientes de otro.',
                'El catálogo de consultorios y las cuentas de pacientes viven en bases aparte que **no contienen historia clínica**.'
            ]
        },
        {
            titulo: 'Con quién se comparten',
            cuerpo: [
                'Con el proveedor de recetas electrónicas, cuando el profesional emite una: se le envían los datos necesarios para el comprobante.',
                'Con el servicio de correo, para mandar confirmaciones de turno y avisos.',
                'Si se activa el sellado en blockchain, lo que se publica es un **hash** —una huella— de la historia, nunca su contenido. De esa huella no se puede reconstruir el texto.',
                '**Falta completar** el detalle de cada proveedor y dónde están alojados los datos.'
            ]
        },
        {
            titulo: 'Derechos sobre los datos',
            cuerpo: [
                'Toda persona puede pedir acceder a sus datos, rectificarlos, actualizarlos y, cuando corresponda, suprimirlos, escribiendo a la dirección de contacto.',
                'La Ley 25.326 da derecho a solicitar el acceso de forma gratuita a intervalos no menores de seis meses.',
                'La Agencia de Acceso a la Información Pública es el órgano de control y atiende las denuncias de quien considere vulnerados sus derechos.'
            ]
        },
        {
            titulo: 'Qué hay que completar antes de publicar',
            cuerpo: [
                'Domicilio y CUIT del responsable, e inscripción de la base de datos ante la Agencia.',
                'Los plazos de conservación tras la baja.',
                'El detalle de proveedores y dónde se alojan los datos.',
                'Y la revisión de alguien que sepa de derecho: esto lo escribió quien programó el sistema.'
            ]
        }
    ]
};

export const DOCUMENTOS = {
    terminos: TERMINOS,
    privacidad: PRIVACIDAD
};
