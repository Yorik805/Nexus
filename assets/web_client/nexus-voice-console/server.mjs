import fs from 'node:fs'
import https from 'node:https'
import path from 'node:path'
import next from 'next'

const root = process.cwd()
const port = Number(process.env.VOICE_CONSOLE_PORT || 3001)
const certificatePath = path.resolve(root, process.env.NEXUS_VOICE_CERT || 'nexus-cert.pem')
const keyPath = path.resolve(root, process.env.NEXUS_VOICE_KEY || 'nexus-key.pem')

if (!fs.existsSync(certificatePath) || !fs.existsSync(keyPath)) {
  throw new Error(`HTTPS certificate or key not found. Expected ${certificatePath} and ${keyPath}.`)
}

const app = next({ dev: false, dir: root })
const handle = app.getRequestHandler()
await app.prepare()

https.createServer({
  cert: fs.readFileSync(certificatePath),
  key: fs.readFileSync(keyPath),
}, (request, response) => handle(request, response)).listen(port, '0.0.0.0', () => {
  console.log(`Nexus Voice Console HTTPS listening on https://0.0.0.0:${port}`)
})
