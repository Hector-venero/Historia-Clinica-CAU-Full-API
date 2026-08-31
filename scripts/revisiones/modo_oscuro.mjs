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
    texto.split('\n').forEach((linea, i) => {
        // Solo dentro de atributos de clase.
        if (!/class=|:class=/.test(linea)) return;
        for (const m of linea.matchAll(SOSPECHOSAS)) {
            const clase = m[1];
            // La pareja tiene que estar en la MISMA linea: es donde vive el elemento.
            const familia = clase.replace(/-(?:white|\d+)$/, '');
            const tieneDark = new RegExp(`dark:${familia}[-\\w/\\[\\]]*`).test(linea);
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
