// Clases de color sin su variante dark:, que dejan una pantalla en claro sobre
// una app oscura. CLAUDE.md lo avisa: "un bg-white o un text-gray-800 sueltos".
import { readFileSync, readdirSync, statSync } from 'fs';
import { join } from 'path';

const vue = (d) => readdirSync(d).flatMap((n) => {
    const p = join(d, n);
    return statSync(p).isDirectory() ? vue(p) : p.endsWith('.vue') ? [p] : [];
});

// Clases claras que necesitan pareja. Se ignoran las que ya son neutras
// (surface-*) porque esas siguen el tema solas.
const SOSPECHOSAS = /(?:^|[\s"'`])(bg-white|bg-gray-(?:50|100|200)|text-gray-(?:700|800|900)|border-gray-(?:200|300)|bg-slate-(?:50|100))(?=[\s"'`]|$)/g;

const hallazgos = [];
for (const f of vue(process.argv[2])) {
    const texto = readFileSync(f, 'utf8');
    const lineas = texto.split('\n');
    lineas.forEach((linea, i) => {
        // Solo dentro de atributos de clase.
        if (!/class=|:class=/.test(linea)) return;
        // Escape para lo deliberado: una seccion que es oscura en los DOS temas
        // lleva colores claros a proposito, y el verificador no puede saberlo.
        // Se marca con `dark-ok` en la linea o en la anterior.
        //
        // Sin esta salida quedaba un hallazgo permanente que no habia que
        // arreglar, y un verificador que grita por algo que esta bien deja de
        // mirarse — que es peor que no tenerlo.
        if (/dark-ok/.test(linea) || /dark-ok/.test(lineas[i - 1] || '')) return;
        for (const m of linea.matchAll(SOSPECHOSAS)) {
            const clase = m[1];
            // La pareja tiene que estar en la MISMA linea: es donde vive el elemento.
            //
            // Se busca por PREFIJO (`dark:text-`) y no por familia exacta
            // (`dark:text-gray`). CLAUDE.md avisa de este error para quien
            // automatice la correccion, y el verificador lo estaba cometiendo:
            // `text-gray-800 dark:text-white` ya esta resuelto a mano, y
            // buscando la familia no se ve y se reporta igual. Eran 9 falsos
            // positivos solo en Dashboard.vue. Con el arreglo, el total paso
            // de 24 hallazgos a 1: casi todo lo que reportaba ya estaba
            // resuelto. Un verificador que grita por cosas que estan bien deja
            // de mirarse, que es peor que no tenerlo.
            const prefijo = clase.split('-')[0]; // bg | text | border
            const tieneDark = new RegExp(`dark:${prefijo}-[-\\w/\\[\\]]+`).test(linea);
            if (!tieneDark) hallazgos.push({ archivo: f.replace(process.argv[2] + '/', ''), linea: i + 1, clase });
        }
    });
}

const porArchivo = {};
for (const h of hallazgos) (porArchivo[h.archivo] ||= []).push(`${h.clase}:${h.linea}`);

const entradas = Object.entries(porArchivo).sort((a, b) => b[1].length - a[1].length);
console.log(`${hallazgos.length} clases claras sin variante dark, en ${entradas.length} archivos\n`);
for (const [archivo, casos] of entradas.slice(0, 15)) {
    console.log(`  ${casos.length.toString().padStart(3)}  ${archivo}`);
}
