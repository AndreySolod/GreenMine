import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    environment: 'happy-dom',
    include: [
      'src/utils/__tests__/**/*.js'
    ],
    coverage: {
      include: ['src/utils/*.js']
    }
  }
})
