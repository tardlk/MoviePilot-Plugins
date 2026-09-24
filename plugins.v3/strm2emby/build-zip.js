import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'
import archiver from 'archiver'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const pluginName = 'strm2emby'

const outputFilePath = path.join(__dirname, `${pluginName}.zip`)
const output = fs.createWriteStream(outputFilePath)
const archive = archiver('zip', {
  zlib: { level: 9 },
})

output.on('close', () => {
  console.log(`\n\x1b[32m[打包成功]\x1b[0m 已生成插件安装包: ${pluginName}.zip`)
  console.log(`\x1b[36m文件大小:\x1b[0m ${(archive.pointer() / 1024).toFixed(2)} KB`)
  console.log('可以直接在 MoviePilot 插件页面上传此 ZIP 文件。\n')
})

archive.on('warning', (err) => {
  if (err.code === 'ENOENT') {
    console.warn('\x1b[33m[打包警告]\x1b[0m', err.message)
  } else {
    throw err
  }
})

archive.on('error', (err) => {
  console.error('\x1b[31m[打包失败]\x1b[0m', err)
  throw err
})

archive.pipe(output)

// 插件运行必需与可选的 Python 文件
const pluginFiles = [
  '__init__.py',
  'guangya_api.py',
  'guangya_client.py',
  'models.py',
]
for (const file of pluginFiles) {
  const filePath = path.join(__dirname, file)
  if (fs.existsSync(filePath)) {
    archive.file(filePath, { name: file })
  } else if (file === '__init__.py') {
    console.error(`\x1b[31m[打包失败]\x1b[0m 缺少必需文件: ${file}`)
    process.exit(1)
  }
}

const distDir = path.join(__dirname, 'dist')
if (fs.existsSync(distDir)) {
  archive.directory(distDir, 'dist')
  console.log('已将完整 dist 目录加入压缩包...')
} else {
  console.warn('\x1b[33m[注意]\x1b[0m 找不到 dist 目录，压缩包将不包含前端产物。')
}

archive.finalize()
