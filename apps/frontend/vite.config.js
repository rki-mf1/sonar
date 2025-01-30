import { fileURLToPath, URL } from 'node:url';
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import ViteGitRevision from "@jinixx/vite-plugin-git-revision";
// https://vitejs.dev/config/
export default defineConfig({
    plugins: [vue(), ViteGitRevision({})],
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
