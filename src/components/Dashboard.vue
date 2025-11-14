<template>
  <div class="dashboard-container">
    <!-- 顶部标题栏 -->
    <div class="header">
      <h1>翰林院-品保</h1>
      <div class="export-info">
        <el-button type="primary" class="export-btn" @click="handleImport">
          導入
        </el-button>
      </div>
    </div>
    <!-- <div class="header">
      <h1>翰林院-品保</h1>
      <div class="export-info">
        <el-button type="primary" class="export-btn" @click="handleImport">
          導入
        </el-button>
      </div>
    </div> -->
    <!-- 導入對話框 -->
    <el-dialog
      v-model="importDialogVisible"
      title="導入課程進度"
      width="520px"
      :close-on-click-modal="false"
    >
      <div class="import-section">
        <p class="import-tip">
          1. 先下載「原始/模板」文件，按照格式填寫或更新課程進度後再上傳。<br />
          2. 支持 Excel (.xlsx) 或 CSV (.csv) 文件，大小不超過 10MB。<br />
          3. 上傳後系統會自動解析並刷新列表。
        </p>

        <el-button
          type="success"
          plain
          size="small"
          :loading="templateLoading"
          @click="handleDownloadTemplate"
          class="download-btn"
        >
          下載原始/模板文件
        </el-button>

        <el-upload
          ref="uploadRef"
          class="upload-area"
          drag
          :auto-upload="false"
          :file-list="fileList"
          :on-change="handleFileChange"
          :on-remove="handleRemove"
          :limit="1"
          accept=".xlsx,.csv"
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">
            將文件拖到此處，或 <em>點擊上傳</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              僅限 1 個文件，格式: .xlsx / .csv，最大 10MB
            </div>
          </template>
        </el-upload>

        <el-alert
          v-if="uploadError"
          :title="uploadError"
          type="error"
          show-icon
          closable
          class="mt-10"
          @close="uploadError = ''"
        />
        <el-alert
          v-if="uploadSuccessMsg"
          :title="uploadSuccessMsg"
          type="success"
          show-icon
          closable
          class="mt-10"
          @close="uploadSuccessMsg = ''"
        />
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="importDialogVisible = false" :disabled="uploading"
            >取消</el-button
          >
          <el-button type="primary" :loading="uploading" @click="submitUpload"
            >開始導入</el-button
          >
        </span>
      </template>
    </el-dialog>

    <!-- 進度詳情對話框 -->
    <el-dialog
      v-model="detailsDialogVisible"
      :title="detailsDialogTitle"
      :width="detailsDialogWidth"
      :close-on-click-modal="true"
    >
      <div
        class="details-scroll"
        :style="{ maxHeight: detailsDialogMaxHeight }"
      >
        <el-table :data="detailsTableData" size="small" stripe>
          <el-table-column prop="id" label="#" width="60" align="center" />
          <el-table-column
            prop="stage"
            label="階段"
            width="160"
            align="center"
          />
          <el-table-column
            prop="status"
            label="狀態"
            width="120"
            align="center"
          />
          <el-table-column
            prop="owner"
            label="負責人"
            width="160"
            align="center"
          />
          <el-table-column prop="updatedAt" label="更新時間" align="center" />
        </el-table>
      </div>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="detailsDialogVisible = false">關閉</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 主要内容区域 -->
    <div class="content">
      <!-- 左侧统计卡片 -->
      <div class="left-panel">
        <div class="stats-card">
          <div class="stat-item">
            <div class="stat-label">課程數</div>
            <div class="stat-value">{{ totalCount }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">完成進度</div>
            <div class="stat-value">{{ completedPercent }}%</div>
          </div>
          <div v-if="loading" class="loading-indicator">
            <div class="loading-text">載入中...</div>
          </div>
          <div v-if="error" class="error-indicator">
            <div class="error-text">{{ error }}</div>
          </div>
        </div>

        <!-- 圆环图 -->
        <div class="chart-container">
          <v-chart class="chart" :option="chartOption" autoresize />
          <div class="chart-legend">
            <div class="legend-item completed">
              <span class="legend-color"></span>
              <span>完成</span>
            </div>
            <div class="legend-item uncompleted">
              <span class="legend-color"></span>
              <span>未完成</span>
            </div>
          </div>
        </div>

        <!-- 底部按钮 -->
        <div class="action-buttons">
          <el-button
            class="action-btn"
            type="primary"
            @click="navigateToLecture"
          >
            <el-icon class="icon-spacing"><Pointer /></el-icon>
            八分鐘試講申請入口
          </el-button>
        </div>
        <div class="action-buttons">
          <el-button
            class="action-btn"
            type="primary"
            @click="navigateToIncubation"
          >
            <el-icon class="icon-spacing"><Pointer /></el-icon>
            講師孵化認證申請入口
          </el-button>
        </div>
      </div>

      <!-- 右侧课程表格 -->
      <div class="right-panel">
        <div class="container">
          <div class="table-header">課程類別：ISO9001</div>
          <div class="update-time">
            最新更新時間：{{ latestUpdateTime || "—" }}
          </div>
        </div>

        <el-table
          :data="courseData"
          row-key="index"
          :loading="loading"
          class="course-table"
          :header-cell-style="{
            backgroundColor: '#1e3a8a',
            color: '#3875c5',
            fontSize: '15px',
            fontWeight: '600',
          }"
          :row-class-name="getRowClassName"
          :max-height="740"
          style="height: 600px"
        >
          <el-table-column
            prop="index"
            label="序号"
            :width="columnWidths.index"
            align="center"
          >
            <template #header>
              <div class="th-content">
                序号
                <span
                  class="col-resizer"
                  @mousedown="onResizeMousedown('index', $event)"
                ></span>
              </div>
            </template>
          </el-table-column>
          <el-table-column
            prop="courseName"
            label="課程名稱"
            :width="columnWidths.courseName"
            align="center"
          >
            <template #default="{ row }">
              <span
                :class="[
                  'clickable-course-name',
                  row.progress === '交付計劃' ? 'complete' : 'incomplete',
                ]"
                @click="navigateToCourseRecord(row.courseName)"
                :title="`点击查看 《${row.courseName}》 的教学记录`"
              >
                {{ row.courseName }}
              </span>
            </template>
            <template #header>
              <div class="th-content">
                課程名稱
                <span
                  class="col-resizer"
                  @mousedown="onResizeMousedown('courseName', $event)"
                ></span>
              </div>
            </template>
          </el-table-column>
          <el-table-column
            prop="dri"
            label="DRI"
            :width="columnWidths.dri"
            align="center"
          >
            <template #header>
              <div class="th-content">
                DRI
                <span
                  class="col-resizer"
                  @mousedown="onResizeMousedown('dri', $event)"
                ></span>
              </div>
            </template>
          </el-table-column>
          <el-table-column
            prop="responsible"
            label="負責人"
            :width="columnWidths.responsible"
            align="center"
          >
            <template #header>
              <div class="th-content">
                負責人
                <span
                  class="col-resizer"
                  @mousedown="onResizeMousedown('responsible', $event)"
                ></span>
              </div>
            </template>
          </el-table-column>
          <el-table-column
            prop="developer"
            label="開發講師"
            :width="columnWidths.developer"
            align="center"
          >
            <template #header>
              <div class="th-content">
                開發講師
                <span
                  class="col-resizer"
                  @mousedown="onResizeMousedown('developer', $event)"
                ></span>
              </div>
            </template>
          </el-table-column>
          <el-table-column
            prop="progress"
            label="進度"
            :width="columnWidths.progress"
            align="center"
          >
            <template #default="{ row }">
              <span
                :class="[
                  'clickable-course-name',
                  row.progress === '交付計劃' ? 'complete' : 'incomplete',
                ]"
                @click="openProgressDialog(row)"
                :title="`点击查看 《${row.courseName}》 的交付详情`"
              >
                {{ row.progress }}
              </span>
            </template>
            <template #header>
              <div class="th-content">
                進度
                <span
                  class="col-resizer"
                  @mousedown="onResizeMousedown('progress', $event)"
                ></span>
              </div>
            </template>
          </el-table-column>
          <!-- <el-table-column
            prop="notes"
            label="備註"
            :width="columnWidths.notes"
            align="center"
          >
            <template #header>
              <div class="th-content">
                備註
                <span
                  class="col-resizer"
                  @mousedown="(e) => startResize('notes', e)"
                ></span>
              </div>
            </template>
          </el-table-column>
          <el-table-column
            prop="delay"
            label="量產Delay"
            :width="columnWidths.delay"
            align="center"
          >
            <template #header>
              <div class="th-content">
                量產Delay
                <span
                  class="col-resizer"
                  @mousedown="(e) => startResize('delay', e)"
                ></span>
              </div>
            </template>
          </el-table-column> -->
          <el-table-column
            prop="avg_teaching_score"
            label="正式交付平均分"
            :width="columnWidths.avg_teaching_score"
            align="center"
          >
            <template #header>
              <div class="th-content">
                正式交付平均分
                <span
                  class="col-resizer"
                  @mousedown="onResizeMousedown('avg_teaching_score', $event)"
                ></span>
              </div>
            </template>
          </el-table-column>
          <el-table-column
            prop="teaching_type_count"
            label="正式交付次数"
            :width="columnWidths.teaching_type_count"
            align="center"
          >
            <template #header>
              <div class="th-content">
                正式交付次数
                <span
                  class="col-resizer"
                  @mousedown="onResizeMousedown('teaching_type_count', $event)"
                ></span>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, onBeforeUnmount, computed } from "vue";
import { useRouter } from "vue-router";
import { Pointer, UploadFilled } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";

const router = useRouter();

// 课程数据状态
const courseData = ref([]);
const loading = ref(false);
const error = ref(null);
const completedCount = ref(0);
const totalCount = ref(0);
const latestUpdateTime = ref("");

// 導入對話框 & 上傳狀態
const importDialogVisible = ref(false);
const fileList = ref([]);
const uploadRef = ref(null);
const uploading = ref(false);
const uploadError = ref("");
const uploadSuccessMsg = ref("");
const templateLoading = ref(false);

// 列宽状态（可拖拽调整）
const columnWidths = ref({
  index: 80,
  courseName: 220,
  dri: 200,
  responsible: 260,
  developer: 260,
  progress: 100,
  notes: 180,
  delay: 180,
  avg_teaching_score: 180,
  teaching_type_count: 180,
});

const RESIZE_MIN = 60;
const RESIZE_MAX = 800;
const resizingState = ref(null); // { key, startX, startWidth }

// 取消列宽持久化：移除本地存储读写，刷新后恢复默认列宽

const onMouseMove = (e) => {
  if (!resizingState.value) return;
  const { key, startX, startWidth } = resizingState.value;
  const delta = e.clientX - startX;
  let next = Math.max(RESIZE_MIN, Math.min(RESIZE_MAX, startWidth + delta));
  // 只取整数像素，避免抖动
  next = Math.round(next);
  columnWidths.value[key] = next;
};

const stopResize = () => {
  if (!resizingState.value) return;
  resizingState.value = null;
  document.removeEventListener("mousemove", onMouseMove);
  document.removeEventListener("mouseup", stopResize);
  document.body.style.cursor = "";
  document.body.style.userSelect = "";
};

const startResize = (key, e) => {
  // 避免触发排序或选中文本
  e.stopPropagation();
  e.preventDefault();
  resizingState.value = {
    key,
    startX: e.clientX,
    startWidth: Number(columnWidths.value[key]) || 120,
  };
  document.addEventListener("mousemove", onMouseMove);
  document.addEventListener("mouseup", stopResize);
  document.body.style.cursor = "col-resize";
  document.body.style.userSelect = "none";
};

// 统一的列宽拖拽事件处理器，避免在模板中创建新函数
const onResizeMousedown = (key, e) => {
  startResize(key, e);
};

onBeforeUnmount(() => {
  // 组件卸载时兜底清理
  document.removeEventListener("mousemove", onMouseMove);
  document.removeEventListener("mouseup", stopResize);
  document.body.style.cursor = "";
  document.body.style.userSelect = "";
});

// 打開導入對話框
const handleImport = () => {
  importDialogVisible.value = true;
};

// 完成进度（百分比）
const completedPercent = computed(() =>
  totalCount.value > 0
    ? Math.round((completedCount.value / totalCount.value) * 100)
    : 0
);

// 下載模板/原始文件
const handleDownloadTemplate = async () => {
  try {
    templateLoading.value = true;
    // 假設後端提供模板下載接口 /api/progress/template
    const resp = await fetch("/api/progress/template");
    if (!resp.ok) throw new Error("下載失敗");
    const blob = await resp.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    // 從header獲取文件名或設置預設
    const disposition = resp.headers.get("Content-Disposition");
    let filename = "progress_template.xlsx";
    if (disposition) {
      // 先嘗試 RFC 5987 filename*
      let matchStar = disposition.match(/filename\*=(?:UTF-8''|"?)([^";]+)"?/i);
      if (matchStar && matchStar[1]) {
        try {
          filename = decodeURIComponent(matchStar[1]);
        } catch (_) {
          filename = matchStar[1];
        }
      } else if (disposition.includes("filename=")) {
        const match = disposition.match(/filename="?([^";]+)"?/);
        if (match && match[1]) {
          try {
            filename = decodeURIComponent(match[1]);
          } catch (_) {
            filename = match[1];
          }
        }
      }
    }
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    ElMessage.success("模板已下載");
  } catch (e) {
    console.error(e);
    ElMessage.error(e.message || "下載模板失敗");
  } finally {
    templateLoading.value = false;
  }
};

// 文件選擇或拖拽變更
const handleFileChange = (file, fileListRaw) => {
  uploadError.value = "";
  uploadSuccessMsg.value = "";
  if (!file || !file.raw) return;
  const rawFile = file.raw;
  const allowTypes = [
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
    "application/vnd.ms-excel",
  ];
  if (!allowTypes.includes(rawFile.type)) {
    uploadError.value = "文件格式僅支持 .xlsx 或 .csv";
    ElMessage.error(uploadError.value);
    // 移除不合法文件
    fileList.value = [];
    nextTick(() => {
      if (uploadRef.value) uploadRef.value.clearFiles();
    });
    return;
  }
  if (rawFile.size / 1024 / 1024 > 10) {
    uploadError.value = "文件大小不能超過 10MB";
    ElMessage.error(uploadError.value);
    fileList.value = [];
    nextTick(() => {
      if (uploadRef.value) uploadRef.value.clearFiles();
    });
    return;
  }
  // 保留第一個
  fileList.value = [rawFile];
};

// 移除文件
const handleRemove = () => {
  fileList.value = [];
};

// 提交上傳
const submitUpload = async () => {
  if (!fileList.value || !fileList.value.length) {
    ElMessage.warning("請先選擇文件");
    return;
  }
  uploading.value = true;
  uploadError.value = "";
  uploadSuccessMsg.value = "";
  try {
    const formData = new FormData();
    formData.append("file", fileList.value[0]);
    // 假設後端解析接口 /api/progress/import (POST)
    const resp = await fetch("/api/progress/import", {
      method: "POST",
      body: formData,
    });
    const result = await resp.json().catch(() => ({}));
    if (!resp.ok || !result.success) {
      throw new Error(result.message || "導入失敗");
    }
    uploadSuccessMsg.value = "導入成功，正在刷新數據...";
    ElMessage.success("導入成功");
    await fetchProgressData();
    fetchUpdateTime();
    // 成功後清空文件
    fileList.value = [];
    // 可選：自動關閉
    setTimeout(() => {
      importDialogVisible.value = false;
      uploadSuccessMsg.value = "";
    }, 1200);
  } catch (e) {
    console.error(e);
    uploadError.value = e.message || "導入過程出現錯誤";
    ElMessage.error(uploadError.value);
  } finally {
    uploading.value = false;
  }
};

// 页面导航功能
const navigateToLecture = () => {
  router.push("/lecture");
};

const navigateToIncubation = () => {
  router.push("/incubation");
};

const navigateToCourseRecord = (courseName) => {
  router.push({
    path: "/teaching-record",
    query: { course: courseName },
  });
};

// API调用函数
const fetchProgressData = async () => {
  loading.value = true;
  error.value = null;

  try {
    // 使用代理路径调用API接口获取数据
    const response = await fetch(`/api/progress?all=true`);
    const data = await response.json();

    if (data.success) {
      courseData.value = data.data.map((item) => ({
        index: item.id,
        courseName: item.courseName,
        dri: item.dri,
        responsible: item.responsible,
        developer: item.developer,
        progress: item.progress,
        avg_teaching_score: item.avg_teaching_score || "/",
        teaching_type_count: item.teaching_type_count || "/",
        notes: item.notes || "/",
        delay: item.delay || "/",
      }));

      totalCount.value = data.data.length;
      completedCount.value = data.data.filter(
        (item) => item.progress === "交付計劃"
      ).length;

      // 更新图表数据
      updateChartData();
    } else {
      throw new Error(data.message || "获取数据失败");
    }
  } catch (err) {
    console.error("获取进度数据失败:", err);
    error.value = err.message || "网络错误，请检查服务器连接";

    // 如果API调用失败，使用默认数据
    loadDefaultData();
  } finally {
    loading.value = false;
  }
};

// 獲取各表最近更新時間（後端聚合）
const fetchUpdateTime = async () => {
  try {
    const resp = await fetch("/api/progress/update_time");
    const data = await resp.json();
    if (data.success) {
      latestUpdateTime.value = data.latest;
    }
  } catch (e) {
    // 靜默失敗
  }
};

// 加载默认数据（API失败时的备用方案）
const loadDefaultData = () => {
  courseData.value = [];
  totalCount.value = 0;
  completedCount.value = 0;
  updateChartData();
};

// 更新图表数据
const updateChartData = () => {
  const uncompletedCount = totalCount.value - completedCount.value;

  chartOption.value = {
    series: [
      {
        type: "pie",
        // padAngle: 5,
        radius: ["50%", "80%"],
        center: ["50%", "50%"],
        data: [
          {
            value: completedCount.value,
            name: "完成",
            itemStyle: { color: "#3875c5" },
          },
          {
            value: uncompletedCount,
            name: "未完成",
            itemStyle: { color: "#c0504d" },
          },
        ],
        label: {
          show: true,
          position: "inside",
          fontSize: 24,
          fontWeight: "bold",
          color: "#ffffff",
          formatter: function (params) {
            return params.value;
          },
          textShadowColor: "rgba(0, 0, 0, 0.8)",
          textShadowBlur: 10,
          textShadowOffsetX: 2,
          textShadowOffsetY: 2,
        },
        labelLine: {
          show: false,
        },
        emphasis: {
          scale: false,
          label: {
            fontSize: 32,
            textShadowBlur: 15,
          },
        },
      },
    ],
  };
};

// 组件挂载时获取数据
onMounted(() => {
  fetchProgressData();
  fetchUpdateTime();
});

// 圆环图配置
const chartOption = ref({
  series: [
    {
      type: "pie",
      radius: ["50%", "80%"],
      center: ["50%", "50%"],
      data: [
        { value: 9, name: "完成", itemStyle: { color: "#4f81bd" } },
        { value: 8, name: "未完成", itemStyle: { color: "#c0504d" } },
      ],
      label: {
        show: true,
        position: "inside",
        fontSize: 24,
        fontWeight: "bold",
        color: "#ffffff",
        formatter: function (params) {
          return params.value;
        },
        textShadowColor: "rgba(0, 0, 0, 0.8)",
        textShadowBlur: 10,
        textShadowOffsetX: 2,
        textShadowOffsetY: 2,
      },
      labelLine: {
        show: false,
      },
      emphasis: {
        scale: false,
        label: {
          fontSize: 32,
          textShadowBlur: 15,
        },
      },
    },
  ],
});

// 表格行样式
const getRowClassName = ({ row }) => {
  if (row.progress === "交付計劃") {
    return "complete-row";
  }
  return "incomplete-row";
};

// 進度詳情對話框狀態
const detailsDialogVisible = ref(false);
const detailsDialogTitle = ref("");
const detailsTableData = ref([]);

// 可調整：詳情對話框寬度與高度（vh）
const detailsDialogWidth = ref("80vw");
const detailsDialogMaxHeight = ref("70vh");

// 打開進度詳情對話框
const openProgressDialog = (row) => {
  const progress = row?.progress ?? "-";
  const courseName = row?.courseName ?? "-";
  detailsDialogTitle.value = `${courseName} - 進度詳情（${progress}）`;
  detailsTableData.value = simulateDetailsFor(courseName, progress);
  detailsDialogVisible.value = true;
};

// 模擬表格數據
const simulateDetailsFor = (courseName, progress) => {
  // 根據不同進度粗略生成 3~5 條示例記錄
  const base = [
    {
      id: 1,
      courseName,
      stage: "需求確認",
      status: progress === "交付計劃" ? "完成" : "進行中",
      owner: "PM-王小明",
      updatedAt: "2025-11-10 10:20",
    },
    {
      id: 2,
      courseName,
      stage: "教案設計",
      status: progress === "交付計劃" ? "完成" : "進行中",
      owner: "講師-李華",
      updatedAt: "2025-11-10 16:05",
    },
    {
      id: 3,
      courseName,
      stage: "試講評審",
      status: progress === "交付計劃" ? "完成" : "待開始",
      owner: "評審組",
      updatedAt: "2025-11-11 09:00",
    },
  ];
  if (progress === "交付計劃") {
    base.push(
      {
        id: 4,
        courseName,
        stage: "正式交付",
        status: "已排程",
        owner: "排程-系統",
        updatedAt: "2025-11-12 14:30",
      },
      {
        id: 5,
        courseName,
        stage: "成效回饋",
        status: "待收集",
        owner: "HR-張美麗",
        updatedAt: "2025-11-13 11:10",
      }
    );
  }
  return base;
};
</script>

<style scoped>
@import "@/style/general.css";

/* 全局默认字体颜色（当前组件范围） */
.dashboard-container {
  color: #3875c5;
}

@keyframes fadeInDown {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.export-info {
  position: absolute;
  right: 10px;
  transform: translateY(18px);
}

.export-btn {
  background: linear-gradient(45deg, #3875c5, #3875c5);
  border: none;
  color: white;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-radius: 8px;
  font-weight: 500;
  letter-spacing: 0.5px;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
  padding: 10px 20px;
  position: relative;
  overflow: hidden;
}

.content {
  display: flex;
  gap: 20px;
  min-height: calc(100vh - 120px);
  height: auto;
  overflow: visible;
}

.left-panel {
  width: 300px;
  display: flex;
  flex-direction: column;
  gap: 35px;
  animation: slideInLeft 0.8s ease-out;
  min-height: fit-content;
  height: auto;
}

@keyframes slideInLeft {
  from {
    opacity: 0;
    transform: translateX(-30px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.stats-card {
  background: rgba(255, 255, 255, 0.12);
  border-radius: 15px;
  padding: 31px;
  backdrop-filter: blur(15px);
  border: 1px solid rgba(255, 255, 255, 0.25);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}
.container {
  display: flex;
  justify-content: space-between;
  width: 100%;
}
.stats-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
  border-color: rgba(255, 255, 255, 0.3);
}

.stat-item {
  text-align: center;
  margin-bottom: 15px;
}

.stat-label {
  color: black;
  font-size: 28px;
  margin-bottom: 5px;
}

.stat-value {
  color: #3875c5;
  font-size: 48px;
  font-weight: bold;
  line-height: 1;
  font-style: italic;
  /* text-shadow: 0 0 20px rgba(96, 217, 250, 0.5); */
  /* animation: pulseShadow 2s ease-in-out infinite; */
}

@keyframes pulseShadow {
  0%,
  100% {
    text-shadow: 0 0 20px rgba(96, 217, 250, 0.5);
  }
  50% {
    text-shadow: 0 0 30px rgba(96, 217, 250, 0.8);
  }
}
.action-btn .icon-spacing {
  margin-right: 15px; /* 控制间隔大小，可根据需求调整 */
}
.chart-container {
  background: rgba(255, 255, 255, 0.12);
  border-radius: 15px;
  padding: 30px;
  backdrop-filter: blur(15px);
  border: 1px solid rgba(255, 255, 255, 0.25);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  text-align: center;
  min-height: 320px;
  transition: all 0.3s ease;
}

.chart-container:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
  border-color: rgba(255, 255, 255, 0.3);
}

.chart {
  width: 100%;
  height: 240px;
}

.chart-legend {
  display: flex;
  justify-content: center;
  gap: 35px;
  margin-top: 25px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #3875c5;
  font-size: 15px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.legend-item.completed:hover {
  transform: scale(1.05);
  color: #3875c5;
}

.legend-item.uncompleted:hover {
  transform: scale(1.05);
  color: #c0504d;
}

/* 未完成：默认文字改为 #c0504d */
.legend-item.uncompleted {
  color: #c0504d;
}

.legend-color {
  width: 14px;
  height: 14px;
  border-radius: 3px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  transition: all 0.3s ease;
}

.legend-item:hover .legend-color {
  transform: scale(1.2);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}

.completed .legend-color {
  background-color: #3875c5;
}

.uncompleted .legend-color {
  background-color: #c0504d;
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.action-btn {
  width: 100%;
  height: 50px;
  background: linear-gradient(45deg, #3875c5, #3875c5);
  border: none;
  color: white;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-radius: 12px;
  font-weight: 500;
  letter-spacing: 0.5px;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(6, 182, 212, 0.3);
  position: relative;
  overflow: hidden;
}

.action-btn::before {
  content: "";
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.2),
    transparent
  );
  transition: left 0.6s ease;
}

.action-btn:hover::before {
  left: 100%;
}

.action-btn:hover {
  background: linear-gradient(45deg, #3875c5, #3875c5);
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(6, 182, 212, 0.4);
}

.action-btn .el-icon {
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.right-panel {
  flex: 1;
  background: rgba(255, 255, 255, 0.12);
  border-radius: 15px;
  padding: 25px;
  backdrop-filter: blur(15px);
  border: 1px solid rgba(255, 255, 255, 0.25);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  animation: slideInRight 0.8s ease-out;
  width: 100%;
  overflow-x: auto;
  max-width: 100%;
  box-sizing: border-box;
}

@keyframes slideInRight {
  from {
    opacity: 0;
    transform: translateX(30px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.table-header {
  color: black;
  font-size: 16px;
  margin-bottom: 15px;
}

.update-time {
  color: black;
  font-size: 16px;
  margin-bottom: 15px;
}

.course-table {
  flex: 1;
  background: transparent;
  width: 100% !important;
}

/* 表头容器 + 拖拽手柄样式 */
:deep(.el-table__header th) .th-content {
  position: relative;
  display: inline-block;
  width: 100%;
  padding-right: 10px;
}

.col-resizer {
  position: absolute;
  top: 0;
  right: -4px; /* 稍微伸出，便于命中 */
  width: 8px;
  height: 100%;
  cursor: col-resize;
  user-select: none;
}

.col-resizer::after {
  content: "";
  position: absolute;
  top: 10%;
  bottom: 10%;
  left: 3px;
  width: 2px;
  background: rgba(255, 255, 255, 0.3);
  transition: background 0.2s ease;
}

.col-resizer:hover::after {
  background: rgba(255, 255, 255, 0.7);
}

:deep(.complete-row) {
  background: rgba(59, 130, 246, 0.1) !important;
}

/* 完成与未完成行的文字颜色统一 */
:deep(.complete-row td) {
  color: #3875c5 !important;
}

:deep(.incomplete-row) {
  background: rgba(239, 68, 68, 0.1) !important;
}

:deep(.incomplete-row td) {
  color: #c0504d;
}

.table-footer {
  background: linear-gradient(45deg, #fbbf24, #f59e0b);
  color: #3875c5;
  padding: 12px;
  text-align: center;
  margin-top: 10px;
  border-radius: 8px;
  font-weight: bold;
  box-shadow: 0 4px 15px rgba(251, 191, 36, 0.3);
  transition: all 0.3s ease;
}

.table-footer:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(251, 191, 36, 0.4);
}

/* 加载和错误状态样式 */
.loading-indicator {
  margin-top: 15px;
  text-align: center;
}

.loading-text {
  color: #3875c5;
  font-size: 14px;
  animation: pulse 1.5s ease-in-out infinite;
}

.error-indicator {
  margin-top: 15px;
  text-align: center;
}

.error-text {
  color: #3875c5;
  font-size: 12px;
  background: rgba(239, 68, 68, 0.1);
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

/* 可点击的课程名称样式 */
.clickable-course-name {
  cursor: pointer;
  font-weight: 600;
  text-decoration: underline;
  text-decoration-color: transparent;
  transition: all 0.3s ease;
  padding: 4px 8px;
  border-radius: 4px;
  display: inline-block;
}

.clickable-course-name.complete {
  color: #3875c5 !important; /* 藍色：正式交付 */
}

.clickable-course-name.incomplete {
  color: #c0504d !important; /* 紅色：非正式交付 */
}

.clickable-course-name:hover {
  text-decoration-color: currentColor;
  background: rgba(96, 217, 250, 0.1);
  transform: scale(1.02);
  box-shadow: 0 2px 8px rgba(96, 217, 250, 0.2);
}

.clickable-course-name.complete:hover {
  color: #3875c5 !important; /* 藍色 hover */
}

.clickable-course-name.incomplete:hover {
  color: #c0504d !important; /* 紅色 hover */
}

.clickable-course-name:active {
  transform: scale(0.98);
  color: #3875c5;
}

/* 導入對話框樣式 */
.import-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-top: 4px;
}

.import-tip {
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.3);
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.6;
  color: #3875c5;
}

.download-btn {
  align-self: flex-start;
}

.upload-area {
  width: 100%;
}

:deep(.upload-area .el-upload-dragger) {
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.6),
    rgba(255, 255, 255, 0.3)
  );
  border: 2px dashed #3b82f6;
  transition: all 0.25s ease;
}

:deep(.upload-area .el-upload-dragger:hover) {
  border-color: #0ea5e9;
  background: rgba(255, 255, 255, 0.8);
}

.mt-10 {
  margin-top: 10px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* 進度詳情對話框內容高度控制 */
.details-scroll {
  overflow: auto;
}
</style>
