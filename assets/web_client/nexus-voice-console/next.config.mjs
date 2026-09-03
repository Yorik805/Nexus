/** @type {import('next').NextConfig} */
import fs from 'node:fs'
import path from 'node:path'

let configuredHost = '127.0.0.1'
try {
  const configPath = path.resolve(process.cwd(), '../../../nexus.config.json')
  configuredHost = JSON.parse(fs.readFileSync(configPath, 'utf8')).host || configuredHost
} catch {}

const nextConfig = {
  allowedDevOrigins: ['localhost', '127.0.0.1', '100.102.195.9', '100.118.250.51', configuredHost],
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
}

export default nextConfig
