import { defineConfig, mergeConfig } from 'vite'
import viteConfig from './vite.config.js'

export default mergeConfig(viteConfig, defineConfig({
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['src/**/*.spec.js'],
    // Vuetify публикует ESM-исходники — их нужно трансформировать
    server: { deps: { inline: ['vuetify'] } },
  },
}))
