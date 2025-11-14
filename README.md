# 翰林院讲师课程分析系统 (Han Web Dashboard)

## 项目简介

翰林院讲师课程分析系统是一个基于 Vue 3 的前端项目，专为翰林院品保部门设计的课程数据分析和讲师管理平台。该系统提供直观的数据可视化界面，帮助管理人员更好地了解课程进度、讲师表现和教学质量等关键指标。

## 主要功能

### 🏠 仪表板概览

- 课程总数统计
- 完成进度跟踪
- 实时数据加载状态
- 错误处理提示

### 📊 数据可视化模块

- **Application_Lecture.vue** - 应用讲座数据分析
- **Incubation_certification.vue** - 孵化认证统计
- **Lecturer_Analysis.vue** - 讲师分析报告
- **teaching_record.vue** - 教学记录管理

### 🎯 核心特性

- 响应式设计，支持多种设备
- 实时数据更新
- 交互式图表展示
- 模块化组件架构

## 技术栈

### 前端框架

- **Vue 3** - 渐进式 JavaScript 框架
- **Vue Router 4** - 官方路由管理器
- **Vite** - 下一代前端构建工具

### UI 组件库

- **Element Plus** - 基于 Vue 3 的组件库
- **Element Plus Icons** - 图标组件

### 数据可视化

- **ECharts** - 百度开源图表库
- **Vue ECharts** - Vue 3 的 ECharts 组件

### HTTP 客户端

- **Axios** - 基于 Promise 的 HTTP 客户端

### 开发工具

- **Express** - Node.js Web 框架（用于模拟服务器）
- **CORS** - 跨域资源共享中间件
- **Concurrently** - 并发运行多个命令

## 项目结构

```
Han-web/
├── public/                 # 静态资源
├── src/                    # 源代码目录
│   ├── assets/            # 静态资源
│   │   ├── favicon.ico    # 网站图标
│   │   └── logo.png       # Logo 图片
│   ├── components/        # 通用组件
│   │   └── Dashboard.vue  # 仪表板主组件
│   ├── moudle/           # 业务模块组件
│   │   ├── Application_Lecture.vue      # 应用讲座模块
│   │   ├── Incubation_certification.vue # 孵化认证模块
│   │   ├── Lecturer_Analysis.vue        # 讲师分析模块
│   │   └── teaching_record.vue          # 教学记录模块
│   ├── router/           # 路由配置
│   │   └── index.js      # 路由定义
│   ├── App.vue           # 根组件
│   └── main.js           # 应用入口
├── MD/                   # 文档目录
│   └── PHOTO_UPLOAD_GUIDE.md # 图片上传指南
├── index.html            # HTML 模板
├── package.json          # 项目配置
├── vite.config.js        # Vite 配置
└── README.md            # 项目说明
```

## 快速开始

### 环境要求

- **Node.js** >= 16.0.0
- **npm** >= 8.0.0 或 **yarn** >= 1.22.0

### 安装依赖

```bash
# 使用 npm
npm install

# 或使用 yarn
yarn install
```

### 启动开发服务器

```bash
# 启动开发服务器（仅前端）
npm run dev

# 启动完整开发环境（包含模拟后端）
npm run start

```

### 构建生产版本

```bash
# 构建生产版本
npm run build

# 预览构建结果（默认运行在 4173 端口）
npm run preview
# 使用不同端口预览
npm run preview -- --port 3001
npm run preview -- --port 8080
```

### npm run preview 所需文件

执行 `npm run preview` 需要以下文件和目录：

#### 1. 必需的构建产物

```
dist/                   # 构建输出目录（必须先执行 npm run build）
├── index.html         # 主 HTML 文件
├── assets/            # 静态资源文件
│   ├── *.js           # JavaScript 打包文件
│   ├── *.css          # CSS 样式文件
│   └── *.ico          # 图标等静态资源
└── ...                # 其他构建产物
```

#### 2. 项目配置文件

```
package.json           # 包含 preview 脚本定义
vite.config.js         # Vite 配置（包含预览服务器配置）
node_modules/          # 依赖包（特别是 Vite 相关包）
```

#### 3. 执行步骤

```bash
# 1. 确保依赖已安装
npm install

# 2. 构建项目（生成 dist 目录）
npm run build

# 3. 预览构建结果
npm run preview
```

#### 4. 预览服务器特点

- **端口**: 默认 4173（Vite 预设）
- **目的**: 预览生产构建版本
- **特性**: 无热重载，模拟生产环境
- **访问**: http://localhost:4173 或 http://192.168.159.97:4173

## 开发指南

### 添加新模块

1. 在 `src/moudle/` 目录下创建新的 Vue 组件
2. 在 `src/router/index.js` 中添加对应路由
3. 在主仪表板中集成新模块

### 组件开发规范

- 使用 Vue 3 Composition API
- 遵循 Element Plus 设计规范
- 组件命名采用 PascalCase
- 文件名采用 snake_case

### 数据可视化

项目使用 ECharts 进行数据可视化：

```javascript
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { BarChart } from "echarts/charts";
import VChart from "vue-echarts";

use([CanvasRenderer, BarChart]);
```

## 部署说明

### 生产环境部署

1. 构建项目：

   ```bash
   npm run build
   ```

2. 将 `dist/` 目录部署到 Web 服务器

3. 配置反向代理（如使用 Nginx）：
   ```nginx
   location / {
     try_files $uri $uri/ /index.html;
   }
   ```

### Docker 部署（可选）

```dockerfile
FROM node:16-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "preview"]
```

## 浏览器支持

- Chrome >= 87
- Firefox >= 78
- Safari >= 14
- Edge >= 88

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 版本历史

- **v0.0.0** - 初始版本
  - 基础仪表板功能
  - 模块化组件架构
  - 数据可视化集成

## 许可证

本项目仅供翰林院内部使用，未经许可不得对外发布或商用。

## 联系信息

如有问题或建议，请联系开发团队：

- 项目负责人：翰林院品保部
- 技术支持：前端开发团队

## 故障排除

### 常见问题

**Q: 启动时提示端口被占用**

```bash
# 检查端口占用
netstat -ano | findstr :3000
# 或修改端口
npm run dev -- --port 3001
```

**Q: 依赖安装失败**

```bash
# 清除缓存
npm cache clean --force
# 删除 node_modules 重新安装
rmdir /s node_modules
npm install
```

**Q: 构建失败**

```bash
# 检查 Node.js 版本
node --version
# 确保版本 >= 16.0.0
```

## 性能优化

- 使用路由懒加载
- 图表组件按需导入
- 静态资源压缩
- 代码分割优化

---

_最后更新：2024 年_
