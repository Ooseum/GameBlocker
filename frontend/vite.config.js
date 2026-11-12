import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base: './' so the built index.html uses relative asset paths — required when
// pywebview loads the file from disk (file:// has no server root).
export default defineConfig({
  plugins: [react()],
  base: './',
  build: { outDir: 'dist', emptyOutDir: true },
})
