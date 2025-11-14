import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [vue()],
    // 降低日志级别，隐藏警告信息
    // logLevel: 'error',
    resolve: {
        alias: {
            '@': resolve(__dirname, 'src'),
            '@assets': resolve(__dirname, 'src/assets')
        }
    },
    assetsInclude: ['**/*.ico'],
    server: {
        host: '0.0.0.0',
        port: 8888,
        open: true,
        proxy: {
            '/api': {
                target: 'http://localhost:1717',
                changeOrigin: true,
                secure: false,
                ws: true,
                configure: (proxy, _options) => {
                    proxy.on('error', (err, _req, _res) => {
                        console.log('proxy error', err);
                    });
                    proxy.on('proxyReq', (proxyReq, req, _res) => {
                        console.log('Sending Request to the Target:', req.method, req.url);
                    });
                    proxy.on('proxyRes', (proxyRes, req, _res) => {
                        console.log('Received Response from the Target:', proxyRes.statusCode, req.url);
                    });
                },
            },
            // 添加静态资源代理，用于访问上传的图片
            '/uploads': {
                target: 'http://localhost:1717',
                changeOrigin: true,
                secure: false,
                configure: (proxy, _options) => {
                    proxy.on('error', (err, _req, _res) => {
                        console.log('uploads proxy error', err);
                    });
                    proxy.on('proxyReq', (proxyReq, req, _res) => {
                        console.log('Sending uploads request:', req.method, req.url);
                    });
                    proxy.on('proxyRes', (proxyRes, req, _res) => {
                        console.log('Received uploads response:', proxyRes.statusCode, req.url);
                    });
                },
            },
            // 追加匯出文件代理
            '/exports': {
                target: 'http://localhost:1717',
                changeOrigin: true,
                secure: false
            }
        }
    },
    preview: {
        host: '0.0.0.0',
        port: 7777,  // 可以修改为其他端口，如 3001
        open: true
    }
})
