# 讲师照片上传功能配置指南

## 功能概述

讲师照片上传功能已集成到讲师分析页面，包含以下特性：

- ✅ 照片上传（支持 JPG、PNG、GIF 等图片格式）
- ✅ 照片预览显示
- ✅ 照片更换
- ✅ 照片删除（带确认对话框）
- ✅ 文件大小限制（5MB）
- ✅ 错误处理和用户反馈
- ✅ 前后端分离架构支持

## 项目结构

```
Hanlin_system/
├── Hanlin/
│   ├── Han-sever/           # 后端服务
│   │   ├── uploads/         # 上传文件目录
│   │   │   └── photos/      # 讲师照片存储
│   │   ├── api/             # API接口
│   │   └── ...
│   └── Han-web/             # 前端项目
│       ├── src/
│       ├── vite.config.js   # 已配置代理
│       ├── .env.development # 开发环境配置
│       ├── .env.production  # 生产环境配置
│       └── ...
```

## 解决方案：前后端分离图片访问

由于您的项目采用前后端分离架构，图片存储在 `Han-sever/uploads/photos/` 目录中，前端需要通过代理访问这些图片。

### 1. Vite 开发服务器配置（已完成）

在 `Han-web/vite.config.js` 中已配置代理：

```javascript
export default defineConfig({
  server: {
    host: "0.0.0.0",
    port: 7777,
    proxy: {
      "/api": {
        target: "http://localhost:3000", // 后端服务地址
        changeOrigin: true,
      },
      "/uploads": {
        target: "http://localhost:3000", // 静态资源代理
        changeOrigin: true,
      },
    },
  },
});
```

### 2. 环境变量配置

#### 开发环境 (.env.development)

```env
# 开发环境使用代理，无需设置API_BASE_URL
# VITE_API_BASE_URL=
```

#### 生产环境 (.env.production)

```env
# 生产环境需要设置完整的服务器地址
VITE_API_BASE_URL=http://your-production-domain.com
```

### 3. 后端服务器静态资源配置

确保您的后端服务器（Han-sever）配置了静态资源服务：

```javascript
// 在您的后端主文件中
app.use("/uploads", express.static(path.join(__dirname, "uploads")));
```

## 使用说明

### 启动服务

1. **启动后端服务** (Han-sever)：

   ```bash
   cd Han-sever
   npm start  # 通常在 http://localhost:3000
   ```

2. **启动前端服务** (Han-web)：
   ```bash
   cd Han-web
   npm run dev  # 通常在 http://localhost:7777
   ```

### 图片访问路径

- **数据库存储**: `/uploads/photos/lecturer_uuid.jpg`
- **前端访问**: `http://localhost:7777/uploads/photos/lecturer_uuid.jpg`
- **实际代理到**: `http://localhost:3000/uploads/photos/lecturer_uuid.jpg`

### 前端代码逻辑

```javascript
const getPhotoUrl = (photoUrl) => {
  if (!photoUrl) return "";

  // 开发环境：通过代理访问
  // 生产环境：通过API_BASE_URL访问
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "";

  if (apiBaseUrl) {
    return `${apiBaseUrl}${photoUrl}`;
  }

  return photoUrl; // 开发环境直接使用相对路径（通过代理）
};
```

## 故障排除

### 图片无法显示的原因及解决方案

1. **后端服务未启动**

   - 确保 Han-sever 在 localhost:3000 运行
   - 检查控制台是否有连接错误

2. **代理配置问题**

   - 重启前端开发服务器
   - 检查 vite.config.js 代理配置
   - 查看浏览器开发者工具的 Network 标签

3. **静态资源服务未配置**

   ```javascript
   // 在后端添加
   app.use("/uploads", express.static(path.join(__dirname, "uploads")));
   ```

4. **文件权限问题**

   - 确保 uploads/photos 目录可读
   - 检查文件是否确实存在

5. **CORS 问题**（生产环境）
   ```javascript
   // 后端添加CORS支持
   app.use(
     cors({
       origin: ["http://localhost:7777", "your-frontend-domain"],
       credentials: true,
     })
   );
   ```

### 调试步骤

1. **检查文件是否存在**：

   ```bash
   ls -la Han-sever/uploads/photos/
   ```

2. **测试直接访问**：
   访问 `http://localhost:3000/uploads/photos/你的图片文件名`

3. **检查代理是否工作**：
   访问 `http://localhost:7777/uploads/photos/你的图片文件名`

4. **查看控制台日志**：
   - 后端服务器日志
   - 前端开发服务器日志
   - 浏览器控制台错误

## 生产部署注意事项

1. **nginx 配置**（如果使用）：

   ```nginx
   server {
     location /uploads/ {
       alias /path/to/Han-sever/uploads/;
     }

     location /api/ {
       proxy_pass http://localhost:3000;
     }
   }
   ```

2. **环境变量设置**：
   确保生产环境的 `VITE_API_BASE_URL` 指向正确的域名

3. **文件上传路径**：
   确保生产环境的文件上传路径正确配置

现在您的图片应该能够正常显示了！
