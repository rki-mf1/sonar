import { readFileSync } from 'node:fs';
import { fileURLToPath, URL } from 'node:url';
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
function readVersionFile() {
    try {
        const version = readFileSync(
            fileURLToPath(new URL('../../VERSION', import.meta.url)),
            'utf8',
        ).trim();
        if (version) {
            return version;
        }
    }
    catch {
        // Docker builds use the app directory as context, so the root VERSION file is absent there.
    }
    try {
        const packageJson = JSON.parse(readFileSync(
            fileURLToPath(new URL('./package.json', import.meta.url)),
            'utf8',
        ));
        if (typeof packageJson.version === 'string' && packageJson.version.trim()) {
            return packageJson.version.trim();
        }
    }
    catch {
        return '0+unknown';
    }
    return '0+unknown';
}
const sonarVersion = process.env.VITE_SONAR_VERSION?.trim()
    || process.env.SONAR_VERSION?.trim()
    || readVersionFile();
// https://vitejs.dev/config/
export default defineConfig({
    plugins: [vue()],
    define: {
        __SONAR_VERSION__: JSON.stringify(sonarVersion),
    },
    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./src', import.meta.url)),
        },
    },
    server: {
        watch: {
            usePolling: true,
        },
    },
});
