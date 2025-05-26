import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import crx from 'vite-plugin-crx-mv3'


// Path to your extension manifest (moved to project root)
const manifestPath = './manifest.json'

export default defineConfig({
  root: '.',            // project root where index.html lives
  plugins: [
    vue(),
    crx({ manifest: manifestPath })
  ],

  build: {
    outDir: 'dist',
    emptyOutDir: true,
    assetsDir: ''
    
  }
})
