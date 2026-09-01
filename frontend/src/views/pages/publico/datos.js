/**
 * Lo que el producto hace, en un solo lugar.
 *
 * La portada, la pagina de funcionalidades, el menu desplegable y la tabla
 * comparativa de precios cuentan lo mismo desde angulos distintos. Con las
 * listas escritas en cada pantalla, agregar una funcion obliga a acordarse de
 * cuatro archivos, y el dia que uno queda viejo el sitio se contradice a si
 * mismo delante de alguien que esta por pagar.
 *
 * REGLA: aca solo entra lo que el sistema hace HOY. Lo que todavia no existe va
 * con `enCamino: true` y se muestra rotulado como tal. Prometer en la portada lo
 * que no esta es la forma mas rapida de que el primer cliente se sienta
 * enganado en la primera semana.
 */

/** Las tres audiencias del sitio. El menu y la pagina de funciones las usan. */
export const AUDIENCIAS = [
    {
        clave: 'profesional',
        titulo: 'Para el profesional',
        bajada: 'Atendes por tu cuenta',
        icono: 'pi-user'
    },
    {
        clave: 'equipo',
        titulo: 'Para la clínica o el equipo',
        bajada: 'Varios profesionales, una agenda',
        icono: 'pi-users'
    },
    {
        clave: 'paciente',
        titulo: 'Para el paciente',
        bajada: 'Tus estudios y tus turnos',
        icono: 'pi-heart'
    }
];

/**
 * Cada funcion, con la audiencia a la que le habla y en que plan entra.
 *
 * `planes` nombra los planes que la incluyen: es lo que dibuja los tildes de la
 * tabla comparativa, y evita mantener esa tabla como una matriz aparte.
 */
export const FUNCIONES = [
    // ─── El profesional ───────────────────────────────────────────────
    {
        titulo: 'Agenda y turnos',
        slug: 'agenda',
        detalle: 'Franjas de atención por día, duración de turno propia, bloqueos y ausencias con o sin aviso.',
        icono: 'pi-calendar',
        audiencia: 'profesional',
        planes: ['profesional', 'equipo'],
        destacada: true
    },
    {
        titulo: 'Turnos online 24 hs',
        slug: 'turnos-online',
        detalle: 'Tus pacientes reservan solos los horarios que dejes libres, desde el celular y a cualquier hora. Vos elegís qué agenda se publica.',
        icono: 'pi-globe',
        audiencia: 'profesional',
        planes: ['profesional', 'equipo'],
        destacada: true
    },
    {
        titulo: 'Historia clínica',
        slug: 'historia-clinica',
        detalle: 'Evoluciones con archivos adjuntos, indicaciones, búsqueda por paciente y toda la historia en una sola ficha.',
        icono: 'pi-book',
        audiencia: 'profesional',
        planes: ['profesional', 'equipo'],
        destacada: true
    },
    {
        titulo: 'Recetas electrónicas',
        slug: 'recetas-electronicas',
        detalle: 'Medicamentos y órdenes de estudio, firmados con tu matrícula y con diagnóstico CIE-10. Se envían por mail o WhatsApp y quedan en la historia.',
        icono: 'pi-file-edit',
        audiencia: 'profesional',
        planes: ['profesional', 'equipo'],
        destacada: true
    },
    {
        titulo: 'Videoconsulta',
        slug: 'videoconsulta',
        detalle: 'Marcás el turno como videollamada y el paciente recibe el enlace por correo y en su portal.',
        icono: 'pi-video',
        audiencia: 'profesional',
        planes: ['profesional', 'equipo'],
        destacada: true
    },
    {
        titulo: 'Recordatorios por mail',
        detalle: 'Confirmación y cancelación automáticas, con la invitación para el calendario adjunta.',
        icono: 'pi-envelope',
        audiencia: 'profesional',
        planes: ['profesional', 'equipo']
    },
    {
        titulo: 'Resumen diario de tu agenda',
        detalle: 'Todas las mañanas, un correo con los turnos del día. Sin entrar al sistema.',
        icono: 'pi-inbox',
        audiencia: 'profesional',
        planes: ['profesional', 'equipo']
    },
    {
        titulo: 'Exportación de la historia clínica',
        detalle: 'La historia completa de un paciente en PDF, con sus adjuntos. Para derivaciones, auditorías o respaldo.',
        icono: 'pi-download',
        audiencia: 'profesional',
        planes: ['profesional', 'equipo']
    },
    {
        titulo: 'Tu propia dirección web',
        detalle: 'tuconsultorio.fichasalud.com.ar, desde el primer día. Es la dirección que le pasás a tus pacientes.',
        icono: 'pi-link',
        audiencia: 'profesional',
        planes: ['profesional', 'equipo']
    },
    {
        titulo: 'Integridad verificable en Blockchain',
        slug: 'integridad-blockchain',
        detalle: 'Sellado de la historia clínica en la Blockchain Federal Argentina: se puede probar que una evolución no se modificó después. Opcional.',
        icono: 'pi-verified',
        audiencia: 'profesional',
        planes: ['profesional', 'equipo'],
        destacada: true
    },

    // ─── El equipo ────────────────────────────────────────────────────
    {
        titulo: 'Varios profesionales',
        slug: 'equipo-profesionales',
        detalle: 'Cada uno con su agenda, su duración de turno y su matrícula, dentro de la misma cuenta.',
        icono: 'pi-users',
        audiencia: 'equipo',
        planes: ['equipo'],
        destacada: true
    },
    {
        titulo: 'Usuario de secretaría',
        slug: 'usuario-secretaria',
        detalle: 'Un rol administrativo que agenda, reprograma y atiende el mostrador sin entrar a la historia clínica.',
        icono: 'pi-id-card',
        audiencia: 'equipo',
        planes: ['equipo'],
        destacada: true
    },
    {
        titulo: 'Historia clínica compartida',
        slug: 'historia-compartida',
        detalle: 'La ficha del paciente es una sola para todo el equipo. Quien lo atienda ve lo que hicieron los demás.',
        icono: 'pi-share-alt',
        audiencia: 'equipo',
        planes: ['equipo'],
        destacada: true
    },
    {
        titulo: 'Agendas de grupo',
        detalle: 'Calendarios compartidos por área o especialidad, con turnos grupales y espacios de rehabilitación.',
        icono: 'pi-calendar-plus',
        audiencia: 'equipo',
        planes: ['equipo']
    },
    {
        titulo: 'Comunicados internos',
        detalle: 'Avisos para todo el equipo. Los normales llegan a la campana; los importantes, además, por mail.',
        icono: 'pi-megaphone',
        audiencia: 'equipo',
        planes: ['equipo']
    },
    {
        titulo: 'Roles y permisos',
        detalle: 'Dirección, profesional, secretaría y referente de área. Cada uno ve lo que le corresponde.',
        icono: 'pi-lock',
        audiencia: 'equipo',
        planes: ['equipo']
    },
    {
        titulo: 'Panel con la actividad del centro',
        detalle: 'Turnos del día, ausencias y actividad reciente de todo el equipo en una pantalla.',
        icono: 'pi-chart-bar',
        audiencia: 'equipo',
        planes: ['equipo']
    },

    // ─── El paciente ──────────────────────────────────────────────────
    {
        titulo: 'Todos tus estudios en un lugar',
        slug: 'portal-del-paciente',
        detalle: 'Las recetas y los estudios que te envían tus profesionales, aunque te atiendas en consultorios distintos.',
        icono: 'pi-folder-open',
        audiencia: 'paciente',
        planes: ['paciente'],
        destacada: true
    },
    {
        titulo: 'Sacá turno sin llamar',
        slug: 'turnos-del-paciente',
        detalle: 'Ves los horarios libres de tu profesional y reservás. A cualquier hora, sin esperar que atiendan el teléfono.',
        icono: 'pi-calendar',
        audiencia: 'paciente',
        planes: ['paciente'],
        destacada: true
    },
    {
        titulo: 'Cancelá a tiempo',
        detalle: 'Si no vas a poder, lo cancelás desde el portal y el horario le queda libre a otra persona.',
        icono: 'pi-times-circle',
        audiencia: 'paciente',
        planes: ['paciente'],
        destacada: true
    },
    {
        titulo: 'Una sola cuenta, para siempre',
        detalle: 'Tus documentos son tuyos: siguen estando aunque cambies de profesional.',
        icono: 'pi-shield',
        audiencia: 'paciente',
        planes: ['paciente']
    },

    // ─── Lo que todavia no esta ───────────────────────────────────────
    // Se muestra rotulado. Que alguien vea que viene en camino es distinto de
    // hacerle creer que ya lo puede usar.
    {
        titulo: 'Recordatorios por WhatsApp',
        detalle: 'Hoy los recordatorios salen por correo.',
        icono: 'pi-whatsapp',
        audiencia: 'profesional',
        planes: [],
        enCamino: true
    },
    {
        titulo: 'Facturación electrónica',
        detalle: 'Integración con ARCA para facturar la consulta.',
        icono: 'pi-dollar',
        audiencia: 'equipo',
        planes: [],
        enCamino: true
    },
    {
        titulo: 'Sincronización con Google Calendar',
        detalle: 'Que tus turnos aparezcan también en tu calendario personal.',
        icono: 'pi-sync',
        audiencia: 'profesional',
        planes: [],
        enCamino: true
    }
];

/** Las funciones de una audiencia. */
export function funcionesDe(audiencia, { incluirEnCamino = false } = {}) {
    return FUNCIONES.filter((f) => f.audiencia === audiencia && (incluirEnCamino || !f.enCamino));
}

/**
 * Los planes.
 *
 * ⚠️ `precio: null` muestra "Consultanos" en vez de un numero. Es a proposito
 * hasta que el precio este definido: poner una cifra de relleno en la pagina de
 * precios es peor que no mostrar ninguna. Para publicarlo, poner el monto
 * mensual en pesos y listo — la tarjeta ya esta armada para recibirlo.
 */
export const PLANES = [
    {
        clave: 'profesional',
        rotulo: 'Para vos solo',
        nombre: 'Profesional',
        bajada: 'Para quien atiende por su cuenta, con o sin secretaria.',
        precio: null,
        destacado: true,
        cta: 'Empezar 30 días gratis',
        ruta: '/registro/medico'
    },
    {
        clave: 'equipo',
        rotulo: 'Para el centro',
        nombre: 'Equipo',
        bajada: 'Varios profesionales sobre la misma historia clínica.',
        precio: null,
        destacado: false,
        cta: 'Solicitar una cuenta',
        ruta: '/registro/institucion'
    }
];

/** El paciente no es un plan pago, pero en la tabla ocupa una columna. */
export const PLAN_PACIENTE = {
    clave: 'paciente',
    nombre: 'Paciente',
    bajada: 'Gratis, siempre.'
};

/**
 * El contenido de la pagina propia de cada funcion.
 *
 * Cada funcion destacada tiene su URL —/funcionalidades/agenda— y todas se
 * dibujan con **un solo componente** a partir de esto. Diez archivos .vue casi
 * iguales serian diez lugares donde arreglar el mismo detalle de diseno, y a la
 * tercera correccion uno queda distinto.
 *
 * `mockup` nombra el dibujo que acompana; el componente resuelve el nombre.
 */
export const PAGINAS = {
    agenda: {
        encabezado: 'Tu agenda, como atendés de verdad',
        promesa: 'Cargás tus días y horarios una vez, y el sistema arma los turnos solo.',
        titulo: 'Se adapta a tu forma de trabajar',
        intro: 'No todos atienden en bloques de 15 minutos ni de lunes a viernes. Definís tus franjas por día y la duración de tu turno, y a partir de ahí la grilla se calcula sola.',
        mockup: 'agenda',
        puntos: [
            'Franjas de atención por día de la semana.',
            'Duración de turno propia para cada profesional.',
            'Ausencias y bloqueos, con o sin aviso al paciente.',
            'Confirmación y cancelación automáticas por correo, con invitación para el calendario.',
            'Un correo todas las mañanas con los turnos del día.'
        ],
        beneficios: [
            { icono: 'pi-clock', titulo: 'Sin superposiciones', detalle: 'El horario ocupado deja de ofrecerse, y la base rechaza dos reservas del mismo turno aunque lleguen a la vez.' },
            { icono: 'pi-envelope', titulo: 'Menos ausencias', detalle: 'El paciente recibe la confirmación con el turno listo para agendar en su celular.' },
            { icono: 'pi-mobile', titulo: 'Desde donde estés', detalle: 'Es una web: entrás desde la computadora del consultorio o desde el teléfono.' }
        ]
    },

    videoconsulta: {
        encabezado: 'Videoconsulta, sin cambiar lo que ya usás',
        promesa: 'Marcás el turno como videollamada y el paciente recibe el enlace donde lo va a buscar.',
        titulo: 'El enlace es tuyo; el resto lo hacemos nosotros',
        intro: 'No te pedimos que aprendas otra herramienta de video ni que tus pacientes instalen nada nuevo. Pegás el enlace de la sala que ya usás —Meet, Zoom, la que sea— y el sistema se ocupa de que llegue a horario y al lugar correcto.',
        mockup: 'agenda',
        puntos: [
            'El turno se marca como presencial o videoconsulta al crearlo.',
            'El paciente recibe el enlace en el correo de confirmación, con un botón para entrar.',
            'La invitación de calendario lleva el enlace en la ubicación: el celular lo abre solo.',
            'También lo ve en su portal, y el botón aparece 30 minutos antes del turno.',
            'Un turno reservado online se puede pasar a videoconsulta después, y el paciente lo ve al instante.'
        ],
        beneficios: [
            { icono: 'pi-link', titulo: 'Tu herramienta, no la nuestra', detalle: 'Seguís usando la sala de siempre. Si mañana cambiás de plataforma, cambiás el enlace y listo.' },
            { icono: 'pi-check-circle', titulo: 'Sin enlaces rotos', detalle: 'El sistema no acepta un enlace que no sea https, así que el error no aparece con el paciente esperando del otro lado.' },
            { icono: 'pi-eye-slash', titulo: 'No grabamos nada', detalle: 'La videollamada pasa por tu herramienta. Ficha Salud guarda el enlace, no la consulta.' }
        ]
    },

    'turnos-online': {
        encabezado: 'Turnos online, 24 horas',
        promesa: 'Tus pacientes reservan solos los horarios que vos dejes libres.',
        titulo: 'Sacate el teléfono de encima',
        intro: 'Publicás tu agenda y el paciente elige entre los horarios que quedaron libres. La reserva entra directo en tu agenda: no hay una lista aparte que alguien tenga que pasar a mano.',
        mockup: 'agenda',
        puntos: [
            'Vos decidís qué agenda se publica: viene apagado por defecto.',
            'El paciente ve solo los horarios realmente libres.',
            'La reserva entra en tu agenda al instante, sin cargarla de nuevo.',
            'Si el paciente cancela a tiempo, el horario vuelve a ofrecerse solo.',
            'Aparecés en el directorio público de la plataforma.'
        ],
        beneficios: [
            { icono: 'pi-moon', titulo: 'Reservan de noche', detalle: 'La mayoría de la gente resuelve estas cosas cuando tu consultorio ya cerró.' },
            { icono: 'pi-shield', titulo: 'Nunca sin tu permiso', detalle: 'Publicar la agenda de alguien sin que lo pida sería repartir su tiempo. Se enciende a mano, profesional por profesional.' },
            { icono: 'pi-refresh', titulo: 'Huecos que se reutilizan', detalle: 'Una cancelación con anticipación libera el horario para otro paciente sin que hagas nada.' }
        ]
    },

    'historia-clinica': {
        encabezado: 'La historia clínica, completa y buscable',
        promesa: 'Todo lo que pasó con un paciente, en una sola ficha y con la firma de quién lo escribió.',
        titulo: 'Una ficha, no una carpeta',
        intro: 'Cada evolución queda con su fecha, su autor y sus archivos. Buscás al paciente y tenés su historia entera, sin revolver papeles ni abrir cinco documentos.',
        mockup: 'equipo',
        puntos: [
            'Evoluciones con fecha, autor e indicaciones.',
            'Archivos adjuntos en la evolución: estudios, imágenes, informes.',
            'Búsqueda por paciente, documento o número de historia.',
            'Exportación completa a PDF, con los adjuntos.',
            'Baja lógica: nada se borra de verdad.'
        ],
        beneficios: [
            { icono: 'pi-search', titulo: 'La encontrás', detalle: 'Buscar por apellido o documento es un segundo. En papel es un cajón.' },
            { icono: 'pi-download', titulo: 'Es tuya', detalle: 'La exportás cuando quieras, para una derivación, una auditoría o para irte a otro sistema.' },
            { icono: 'pi-lock', titulo: 'Con acceso controlado', detalle: 'La secretaría gestiona los turnos sin entrar a la historia clínica.' }
        ]
    },

    'recetas-electronicas': {
        encabezado: 'Recetas electrónicas y órdenes de estudio',
        promesa: 'Emitidas con tu matrícula, enviadas al paciente y guardadas en su historia.',
        titulo: 'Recetás y ya está',
        intro: 'Buscás el medicamento, elegís el diagnóstico y emitís. Sale con tus datos profesionales y tu lugar de atención, no con una plantilla genérica, y queda como una evolución en la historia del paciente: una receta es un acto médico.',
        mockup: 'receta',
        puntos: [
            'Medicamentos con buscador, y órdenes de estudio en texto libre.',
            'Diagnóstico CIE-10 con autocompletado.',
            'Tus datos de matrícula y tu lugar de atención, tomados de tu perfil.',
            'Envío por correo o WhatsApp, y descarga del PDF.',
            'Anulación de una receta ya emitida.'
        ],
        beneficios: [
            { icono: 'pi-file-edit', titulo: 'Queda registrado', detalle: 'Cada emisión deja su evolución en la historia clínica, sin que tengas que escribirla.' },
            { icono: 'pi-send', titulo: 'Le llega ahora', detalle: 'El paciente la recibe antes de salir del consultorio, y también le queda en su portal.' },
            { icono: 'pi-times-circle', titulo: 'Se puede anular', detalle: 'Si te equivocaste, se anula y queda constancia. Cada estudio se anula por separado.' }
        ]
    },

    'integridad-blockchain': {
        encabezado: 'Integridad verificable en Blockchain',
        promesa: 'Se puede probar que una evolución no se modificó después de escrita.',
        titulo: 'Para cuando alguien lo discuta',
        intro: 'La historia se sella en la Blockchain Federal Argentina: queda una constancia con fecha de que ese contenido existía tal cual. Si después alguien lo cambia, la verificación lo dice. Es opcional y no cambia en nada la forma de trabajar.',
        mockup: 'sello',
        puntos: [
            'Sellado de la historia consolidada y de cada evolución por separado.',
            'Constancia con fecha, sobre una blockchain pública argentina.',
            'La verificación distingue "pendiente" de "no coincide": un sello recién hecho no es una adulteración.',
            'Los sellos no se pisan: cada uno queda con su recibo.',
            'Opcional, y sin costo extra.'
        ],
        beneficios: [
            { icono: 'pi-verified', titulo: 'Prueba, no promesa', detalle: 'No es que el sistema diga que no se modificó: se verifica contra un registro que no controlamos nosotros.' },
            { icono: 'pi-flag', titulo: 'Hecha en Argentina', detalle: 'La Blockchain Federal Argentina es una red pública impulsada por organismos del país.' },
            { icono: 'pi-eye', titulo: 'Sin cambiar tu rutina', detalle: 'Cargás la evolución como siempre; el sellado pasa por detrás.' }
        ]
    },

    'equipo-profesionales': {
        encabezado: 'Todo el equipo, una sola cuenta',
        promesa: 'Cada profesional con su agenda y su matrícula, dentro del mismo centro.',
        titulo: 'Coordinado, no disperso',
        intro: 'Das de alta a cada integrante con su especialidad, su duración de turno y sus horarios. La agenda del centro se ve completa o profesional por profesional, y los pacientes son los del centro, no los de cada uno por su lado.',
        mockup: 'agenda',
        puntos: [
            'Alta y baja de profesionales, con su matrícula y especialidad.',
            'Agenda propia y duración de turno propia para cada uno.',
            'Agendas de grupo por área, con turnos grupales.',
            'Comunicados internos para todo el equipo.',
            'Panel con los turnos y la actividad del día.'
        ],
        beneficios: [
            { icono: 'pi-users', titulo: 'Una sola dirección', detalle: 'El centro tiene su web y su equipo adentro: el paciente no tiene que saber a qué sistema entrar.' },
            { icono: 'pi-calendar-plus', titulo: 'Agendas compartidas', detalle: 'Para rehabilitación, talleres o cualquier atención de a varios.' },
            { icono: 'pi-megaphone', titulo: 'Avisos que se leen', detalle: 'Los normales van a la campana; los importantes, además, por correo. Un mail por cada aviso logra que no se lea ninguno.' }
        ]
    },

    'usuario-secretaria': {
        encabezado: 'Usuario de secretaría',
        promesa: 'Agenda, reprograma y atiende el mostrador. Sin entrar a la historia clínica.',
        titulo: 'Cada uno ve lo suyo',
        intro: 'El rol administrativo trabaja todo el día con los turnos y los datos de contacto, que es lo que necesita, y no tiene acceso a las evoluciones. No es que la pantalla se le oculte: el servidor se lo niega.',
        mockup: 'roles',
        puntos: [
            'Cuatro roles: dirección, profesional, secretaría y referente de área.',
            'La secretaría gestiona turnos y pacientes, no la historia clínica.',
            'El permiso se valida en el servidor, no escondiendo un botón.',
            'Queda registrado quién agendó cada turno.',
            'Baja de un usuario sin borrar lo que hizo.'
        ],
        beneficios: [
            { icono: 'pi-lock', titulo: 'Confidencialidad real', detalle: 'Ocultar una opción del menú no es un permiso. Acá el acceso se corta del lado del servidor.' },
            { icono: 'pi-history', titulo: 'Trazabilidad', detalle: 'Cada turno guarda quién lo creó, además de a qué profesional pertenece.' },
            { icono: 'pi-user-minus', titulo: 'Bajas sin pérdida', detalle: 'Quien deja el equipo pierde el acceso, pero su trabajo queda en la historia.' }
        ]
    },

    'historia-compartida': {
        encabezado: 'Historia clínica compartida',
        promesa: 'La ficha del paciente es una sola para todo el centro.',
        titulo: 'El que atiende, ve todo',
        intro: 'Si el paciente vino la semana pasada por otra cosa y lo atendió otro profesional, eso está en la misma ficha y con la firma de quien lo escribió. Es lo que hace posible la atención interdisciplinaria sin llamarse por teléfono.',
        mockup: 'equipo',
        puntos: [
            'Una ficha por paciente, compartida por el equipo.',
            'Cada evolución con su autor y su fecha.',
            'Adjuntos visibles para todo el centro.',
            'Búsqueda única: el paciente no está duplicado por profesional.',
            'La misma historia alimenta las recetas y el portal del paciente.'
        ],
        beneficios: [
            { icono: 'pi-share-alt', titulo: 'Sin repetir la anamnesis', detalle: 'El paciente no tiene que contar su historia de nuevo en cada consultorio del mismo centro.' },
            { icono: 'pi-sitemap', titulo: 'Interdisciplina', detalle: 'Kinesiología, clínica y traumatología sobre el mismo cuadro, viendo lo mismo.' },
            { icono: 'pi-database', titulo: 'Aislada de otros centros', detalle: 'Compartida adentro, invisible afuera: cada centro tiene su propia base de datos.' }
        ]
    },

    'portal-del-paciente': {
        encabezado: 'El portal del paciente',
        promesa: 'Sus estudios y recetas, de todos sus profesionales, en un solo lugar. Gratis.',
        titulo: 'Lo que le mandaste no se pierde',
        intro: 'El paciente entra con su cuenta y ve lo que le enviaron sus profesionales, aunque se atienda en consultorios distintos. La identidad es su documento, así que dos lugares distintos le llegan a la misma persona.',
        mockup: 'buzon',
        puntos: [
            'Recetas, órdenes y estudios de todos sus profesionales.',
            'Una copia propia: si un consultorio se da de baja, sus documentos siguen ahí.',
            'Cuenta gratuita, con verificación del correo.',
            'Sus turnos, con la posibilidad de cancelarlos.',
            'Nadie ve la historia clínica: solo lo que un profesional decidió enviarle.'
        ],
        beneficios: [
            { icono: 'pi-folder-open', titulo: 'No lo pierde', detalle: 'Se acabó el "lo tengo en el WhatsApp de mi hija".' },
            { icono: 'pi-users', titulo: 'Suma consultorios', detalle: 'Cuantos más profesionales le envían, más útil se vuelve el portal para él, y más pacientes traen tus colegas.' },
            { icono: 'pi-shield', titulo: 'Separado de tu sistema', detalle: 'La cuenta del paciente vive en otro plano: no le da acceso a nada de tu consultorio.' }
        ]
    },

    'turnos-del-paciente': {
        encabezado: 'Sacar turno sin llamar',
        promesa: 'El paciente elige entre los horarios libres y reserva desde el celular.',
        titulo: 'A la hora que le queda cómodo',
        intro: 'Busca a su profesional, ve los horarios disponibles y reserva. Si no va a poder ir, lo cancela con anticipación y el horario le queda libre a otro. No hay teléfono ocupado ni "te confirmo mañana".',
        mockup: 'agenda',
        puntos: [
            'Horarios reales, tomados de la agenda del profesional.',
            'Reserva a cualquier hora, desde el teléfono.',
            'Confirmación por correo, con la invitación para el calendario.',
            'Cancelación desde el portal, con la anticipación que el consultorio defina.',
            'Todos sus turnos, de todos sus profesionales, en una lista.'
        ],
        beneficios: [
            { icono: 'pi-phone', titulo: 'Menos llamados', detalle: 'La secretaría deja de usar la mañana en atender el teléfono para dar horarios.' },
            { icono: 'pi-check-circle', titulo: 'Menos ausencias', detalle: 'El que reserva solo y recibe la confirmación falta menos.' },
            { icono: 'pi-refresh', titulo: 'Huecos aprovechados', detalle: 'Una cancelación a tiempo vuelve a ofrecerse en vez de quedar vacía.' }
        ]
    }
};

/** La funcion que corresponde a una pagina, por su slug. */
export function funcionPorSlug(slug) {
    return FUNCIONES.find((f) => f.slug === slug) || null;
}

/** Las funciones que tienen pagina propia, en el orden en que estan escritas. */
export const CON_PAGINA = FUNCIONES.filter((f) => f.slug && PAGINAS[f.slug]);

/**
 * A donde escribe alguien que quiere hablar con una persona.
 *
 * ⚠️ El dominio todavia no esta registrado. Este es el unico lugar donde
 * cambiarlo: lo usan el pie del sitio publico y la pantalla del plan dentro del
 * sistema, y dos copias de una direccion de correo divergen a la primera
 * mudanza.
 */
export const CORREO_CONTACTO = 'hola@fichasalud.com.ar';
