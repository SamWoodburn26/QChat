import fs from 'node:fs'
import path from 'node:path'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

const certDir = path.resolve(process.cwd(), '.cert')
const certificatePath = path.join(certDir, 'localhost-cert.pem')
const keyPath = path.join(certDir, 'localhost-key.pem')
const backendSettingsPath = path.resolve(process.cwd(), 'src', 'backend', 'local.settings.json')

const backendSettings = JSON.parse(fs.readFileSync(backendSettingsPath, 'utf-8')) as {
  Values?: {
    SERVER_URL?: string
  }
}

const fallbackBackendTarget = backendSettings.Values?.SERVER_URL || 'http://localhost:7071'
const hasHttpsCertificates = fs.existsSync(certificatePath) && fs.existsSync(keyPath)
const defaultPort = hasHttpsCertificates ? 443 : 800
const configuredPort = Number.parseInt(process.env.VITE_PORT || '', 10)
const serverPort = Number.isFinite(configuredPort) ? configuredPort : defaultPort

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendTarget = env.VITE_SERVER_URL || env.SERVER_URL || fallbackBackendTarget

  return {
    plugins: [react()],
    server: {
      host: '0.0.0.0',
      port: serverPort,
      strictPort: true,
      https: hasHttpsCertificates
        ? {
            cert: fs.readFileSync(certificatePath),
            key: fs.readFileSync(keyPath),
          }
        : undefined,
      proxy: {
        '/api': {
          target: backendTarget,
          changeOrigin: true,
          secure: false,
        },
      },
    },
    json: {
      stringify: false,
    },
  }
})
