// Enlaces estaticos que no coinciden con ninguna ruta declarada.
// Es lo que habria encontrado el /portal/perfil roto sin tener que hacer clic.
import { readFileSync, readdirSync, statSync } from 'fs';
import { join } from 'path';

const raiz = process.argv[2];

function archivos(dir) {
    return readdirSync(dir).flatMap((n) => {
        const p = join(dir, n);
        return statSync(p).isDirectory() ? archivos(p) : p.endsWith('.vue') ? [p] : [];
    });
}

// Rutas declaradas, con los parametros vueltos comodin.
const router = readFileSync(join(raiz, 'router/index.js'), 'utf8');
const declaradas = [...router.matchAll(/path:\s*'([^']*)'/g)].map((m) => m[1]);

// Se arman las rutas completas: las hijas cuelgan del padre. Aproximacion
// suficiente para detectar un destino que no existe en ningun lado.
// Las hijas se declaran relativas ('turnos'), asi que hay que componerlas con
// cada padre absoluto. Se compone contra todos: alcanza para detectar un destino
// que no existe en ningun lado, que es lo que se busca.
const absolutas = declaradas.filter((p) => p.startsWith('/'));
const relativas = declaradas.filter((p) => !p.startsWith('/') && p !== '');
const completas = [
    ...absolutas,
    ...absolutas.flatMap((base) => relativas.map((hija) => `${base.replace(/\/$/, '')}/${hija}`))
];
const patrones = completas.map((p) => new RegExp('^/?' + p.replace(/:[^/]+/g, '[^/]+').replace(/^\//, '') + '$'));

const problemas = [];
for (const f of archivos(join(raiz, 'views')).concat(archivos(join(raiz, 'layout')))) {
    const txt = readFileSync(f, 'utf8');
    for (const m of txt.matchAll(/\bto="(\/[^"{}]*)"/g)) {
        const destino = m[1].replace(/\/$/, '') || '/';
        const limpio = destino.replace(/^\//, '');
        const existe = patrones.some((re) => re.test(limpio)) || declaradas.includes(destino);
        if (!existe) problemas.push(`${f.replace(raiz + '/', '')}  ->  ${destino}`);
    }
}

if (problemas.length) {
    console.log('Destinos sin ruta declarada:');
    for (const p of [...new Set(problemas)].sort()) console.log('  ' + p);
} else {
    console.log('Todos los enlaces estaticos apuntan a una ruta declarada.');
}
