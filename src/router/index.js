import { createRouter, createWebHashHistory } from 'vue-router'
import Dashboard from '../components/Dashboard.vue'
import ApplicationLecture from '../moudle/Application_Lecture.vue'
import IncubationCertification from '../moudle/Incubation_certification.vue'
import TeachingRecord from '../moudle/teaching_record.vue'
import LecturerAnalysis from '../moudle/Lecturer_Analysis.vue'

const routes = [
    {
        path: '/',
        name: 'Dashboard',
        component: Dashboard,
        meta: {
            title: '翰林院-品保 - 主面板'
        }
    },
    {
        path: '/lecture',
        name: 'ApplicationLecture',
        component: ApplicationLecture,
        meta: {
            title: '翰林院-品保 - 八分鐘試講申請'
        }
    },
    {
        path: '/incubation',
        name: 'IncubationCertification',
        component: IncubationCertification,
        meta: {
            title: '翰林院-品保 - 講師孵化認證申請'
        }
    },
    {
        path: '/teaching-record',
        name: 'TeachingRecord',
        component: TeachingRecord,
        meta: {
            title: '翰林院-品保 - 教學記錄'
        }
    },
    {
        path: '/lecturer-analysis',
        name: 'LecturerAnalysis',
        component: LecturerAnalysis,
        meta: {
            title: '翰林院-品保 - 講師分析'
        }
    }
]

// 使用 Hash 模式避免后端未配置 SPA 回退时刷新 404
// 如需 History 模式，请改回 createWebHistory() 并在後端添加通配回退到 index.html
const router = createRouter({
    history: createWebHashHistory(),
    routes,
    // 可选：统一滚动行为
    scrollBehavior() {
        return { top: 0 }
    }
})

// 全局路由守卫 - 设置页面标题
router.beforeEach((to, from, next) => {
    if (to.meta.title) {
        document.title = to.meta.title
    }
    next()
})

export default router
