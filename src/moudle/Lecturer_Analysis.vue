<template>
  <div class="dashboard-container">
    <div class="header">
      <h1>翰林院-品保</h1>
    </div>
    <div class="top-nav">
      <div class="back-section" style="padding-left: 30px">
        <el-button class="back-btn custom-btn" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          <span class="btn-text">返回</span>
        </el-button>
        <el-button
          class="refresh-btn custom-btn"
          @click="refreshPage"
          :loading="refreshing"
          :disabled="refreshing || loading"
        >
          <el-icon><Refresh /></el-icon>
          <span class="btn-text">{{ refreshing ? "刷新中..." : "刷新" }}</span>
        </el-button>
      </div>
      <!-- 右上角下拉选择器 -->
      <div class="header-controls">
        <el-select
          v-model="selectedLecturer"
          @change="handleNameChange"
          :placeholder="lecturerFromParams"
          class="lecturer-select"
          size="default"
          filterable
          clearable
        >
          <el-option
            v-for="lecturer in lecturerOptions"
            :key="lecturer.value"
            :label="lecturer.label"
            :value="lecturer.value"
          ></el-option>
        </el-select>
      </div>
    </div>

    <!-- 主要内容区域 -->
    <div class="content">
      <!-- 左侧讲师信息区域 -->
      <div class="lecturer-info-section">
        <!-- 讲师照片 -->
        <div class="lecturer-photo">
          <div class="photo-container" @click="triggerFileUpload">
            <!-- 显示已上传的图片 -->
            <img
              v-if="lecturerInfo.photoUrl"
              :src="getPhotoUrl(lecturerInfo.photoUrl)"
              alt="讲师照片"
              class="lecturer-image"
              @error="handleImageError"
              @load="handleImageLoad"
            />
            <!-- 默认占位符 -->
            <div v-else class="photo-placeholder">
              <div class="placeholder-content">
                <el-icon class="upload-icon"><Camera /></el-icon>
                <span class="placeholder-text">點擊上傳照片</span>
              </div>
            </div>
            <!-- 上传进度遮罩 -->
            <div v-if="uploading" class="upload-overlay">
              <el-icon class="loading-icon"><Loading /></el-icon>
              <span>上傳中...</span>
            </div>
          </div>
          <!-- 隐藏的文件输入 -->
          <input
            ref="fileInput"
            type="file"
            accept="image/*"
            @change="handleFileUpload"
            style="display: none"
          />
          <!-- 操作按钮 -->
          <div v-if="lecturerInfo.photoUrl" class="photo-actions">
            <el-button
              size="small"
              type="primary"
              @click.stop="triggerFileUpload"
              class="action-btn"
            >
              更換照片
            </el-button>
            <el-button
              size="small"
              type="danger"
              @click.stop="removePhoto"
              class="action-btn"
            >
              刪除照片
            </el-button>
          </div>
        </div>

        <!-- 讲师详细信息 -->
        <div class="lecturer-details">
          <div class="info-row">
            <span class="info-label">【講師】</span>
            <span class="info-value">{{
              lecturerInfo.name || selectedLecturer
            }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">【類別】</span>
            <span class="info-value">{{ lecturerInfo.category }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">【部門】</span>
            <span class="info-value">{{ lecturerInfo.department }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">【簡介】</span>
            <span class="info-value">{{ lecturerInfo.introduction }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">【分機】</span>
            <span class="info-value">{{ lecturerInfo.extension_number }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">【手機】</span>
            <span class="info-value">{{ lecturerInfo.phon_number }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">【郵箱】</span>
            <span class="info-value">{{ lecturerInfo.email_number }}</span>
          </div>
        </div>
      </div>

      <!-- 右侧统计信息区域 -->
      <div class="statistics-section">
        <div class="stats-grid">
          <!-- 试点统计 -->
          <div class="stat-card">
            <div class="stat-label">試點：</div>
            <div class="stat-value red">{{ statisticsData.pilot.count }}</div>
            <div class="stat-label">均分：</div>
            <span class="stat-value red">{{
              statisticsData.pilot.average
            }}</span>
          </div>

          <!-- 试跑统计 -->
          <div class="stat-card">
            <div class="stat-label">試跑：</div>
            <div class="stat-value red">{{ statisticsData.trial.count }}</div>
            <div class="stat-label">均分：</div>
            <span class="stat-value red">{{
              statisticsData.trial.average
            }}</span>
          </div>

          <!-- 正式交付统计 -->
          <div class="stat-card">
            <div class="stat-label">正式交付：</div>
            <div class="stat-value red">{{ statisticsData.formal.count }}</div>
            <div class="stat-label">均分：</div>
            <span class="stat-value red">{{
              statisticsData.formal.average
            }}</span>
          </div>
        </div>

        <!-- 导出按钮 -->
        <div class="export-section">
          <el-button type="primary" class="export-btn" @click="handleExport">
            導出
          </el-button>
        </div>
      </div>
    </div>

    <!-- 下方图表区域 -->
    <div class="main-chart" ref="chartContainer"></div>
  </div>
</template>

<script>
import {
  ref,
  reactive,
  onMounted,
  onUnmounted,
  nextTick,
  computed,
  watch,
} from "vue";
import { useRoute, useRouter } from "vue-router";
import { ArrowLeft, Camera, Loading } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import * as echarts from "echarts";

export default {
  name: "LecturerAnalysis",
  setup() {
    const route = useRoute();
    const router = useRouter();

    // 生成时间戳用于文件命名
    const now = new Date();
    const pad = (n) => n.toString().padStart(2, "0");
    const timestamp = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(
      now.getDate()
    )}${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;

    // 从URL参数获取讲师名称，如果没有则使用默认值
    const chartContainer = ref(null);
    const refreshing = ref(false);
    const loading = ref(false);
    let chart = null;
    let resizeHandler = null; // 添加 resize 处理函数引用

    // 计算属性获取当前讲师名称
    const lecturerFromParams = computed(() => route.query.lecturer);
    const selectedLecturer = ref(lecturerFromParams.value);
    // console.log("Name:", lecturerFromParams.value);

    // 讲师选项 - 将通过API动态获取
    const lecturerOptions = ref([]);

    // 获取讲师选项
    const fetchLecturerOptions = async () => {
      try {
        const response = await fetch("/api/lecturer-analysis/name-options");
        const data = await response.json();
        lecturerOptions.value = data.Options || [];
      } catch (error) {
        console.error("获取讲师选项失败:", error);
        // 设置默认选项作为后备
        lecturerOptions.value = [];
      }
    };

    // 处理讲师变更
    const handleNameChange = (nameValue) => {
      router.push({ query: { ...route.query, lecturer: nameValue } });
      // 延迟执行确保路由更新完成
      nextTick(() => {
        fetchLecturerData();
      });
    };

    // 获取讲师统计数据
    // const fetchLecturerStats = async () => {
    //   if (!selectedLecturer.value) return;

    //   try {
    //     const response = await fetch(
    //       `/api/lecturer-analysis/stats?lecturer_name=${encodeURIComponent(
    //         selectedLecturer.value
    //       )}`
    //     );
    //     const data = await response.json();

    //     if (data.success && data.data) {
    //       // 更新统计数据
    //       statisticsData.pilot.count = data.data.pilot?.count || 0;
    //       statisticsData.pilot.average = data.data.pilot?.average || 0;
    //       statisticsData.trial.count = data.data.trial?.count || 0;
    //       statisticsData.trial.average = data.data.trial?.average || 0;
    //       statisticsData.formal.count = data.data.formal?.count || 0;
    //       statisticsData.formal.average = data.data.formal?.average || 0;
    //     }
    //   } catch (error) {
    //     console.error("获取讲师统计数据失败:", error);
    //   }
    // };

    // 获取讲师相关的所有数据
    const fetchLecturerData = async () => {
      if (!selectedLecturer.value) return;
      // 切换讲师时先清空旧数据，避免短暂残留上一讲师内容
      clearLecturerData();
      loading.value = true;
      try {
        // 并行获取基本数据
        await Promise.all([
          fetchLecturerInfo(),
          fetchLecturerscore(),
          // fetchLecturerStats(),
        ]);

        // 基本数据获取完成后，再获取图表数据
        await fetchLecturerChartData();
      } catch (error) {
        console.error("获取讲师数据失败:", error);
        clearLecturerData();
      } finally {
        loading.value = false;
      }
    };

    // 讲师详细信息
    const lecturerInfo = reactive({
      name: "",
      category: "",
      department: "",
      introduction: "",
      contact: "",
      photoUrl: "", // 添加照片URL字段
    });

    // 清空所有与当前讲师相关的数据（除选中讲师名，保留名称用于显示）
    const clearLecturerData = () => {
      lecturerInfo.name = selectedLecturer.value || "";
      lecturerInfo.category = "";
      lecturerInfo.department = "";
      lecturerInfo.introduction = "";
      lecturerInfo.extension_number = "";
      lecturerInfo.phon_number = "";
      lecturerInfo.email_number = "";
      lecturerInfo.contact = "";
      lecturerInfo.photoUrl = "";
      statisticsData.pilot.count = 0;
      statisticsData.pilot.average = 0;
      statisticsData.trial.count = 0;
      statisticsData.trial.average = 0;
      statisticsData.formal.count = 0;
      statisticsData.formal.average = 0;
      chartData.xAxisLabels = [];
      chartData.dynamicSeries = [];
      chartData.separatorLines = [];
      chartData.stageLabels = [];
      if (chart) {
        chart.dispose();
        chart = null;
      }
    };

    // 照片上传相关状态
    const fileInput = ref(null);
    const uploading = ref(false);

    // 获取讲师详细信息
    const fetchLecturerInfo = async () => {
      if (!selectedLecturer.value) return;

      try {
        const response = await fetch(
          `api/lecturer-analysis/teachingdata?lecturer_name=${encodeURIComponent(
            selectedLecturer.value
          )}`
        );
        const lecturerInfoData = await response.json();
        // console.log("lecturerInfoData:", lecturerInfoData.data.name);
        if (lecturerInfoData.success && lecturerInfoData.data) {
          lecturerInfo.name =
            lecturerInfoData.data.name || selectedLecturer.value;
          lecturerInfo.category =
            "翰林院" + lecturerInfoData.data.teaching_instructor_type || "";
          lecturerInfo.department = lecturerInfoData.data.department || "";
          lecturerInfo.introduction = lecturerInfoData.data.introduction || "";
          lecturerInfo.extension_number =
            lecturerInfoData.data.extension_number || "";
          lecturerInfo.phon_number = lecturerInfoData.data.phon_number || "";
          lecturerInfo.email_number = lecturerInfoData.data.email_number || "";
          lecturerInfo.contact =
            lecturerInfoData.data.phon_number +
              "➕" +
              lecturerInfoData.data.email_number || "";
          // 获取讲师照片URL
          lecturerInfo.photoUrl = lecturerInfoData.data.photo_upload || "";
        } else {
          // API返回空：保持清空，仅更新名称
          lecturerInfo.name = selectedLecturer.value;
          lecturerInfo.category = "";
          lecturerInfo.department = "";
          lecturerInfo.introduction = "";
          lecturerInfo.extension_number = "";
          lecturerInfo.phon_number = "";
          lecturerInfo.email_number = "";
          lecturerInfo.contact = "";
          lecturerInfo.photoUrl = "";
        }
      } catch (error) {
        console.error("获取讲师详细信息失败:", error);
        lecturerInfo.name = selectedLecturer.value;
        lecturerInfo.category = "";
        lecturerInfo.department = "";
        lecturerInfo.introduction = "";
        lecturerInfo.extension_number = "";
        lecturerInfo.phon_number = "";
        lecturerInfo.email_number = "";
        lecturerInfo.contact = "";
        lecturerInfo.photoUrl = "";
      }
    };

    // 统计数据  pilot試點  trial試跑  formal正式交付
    const statisticsData = reactive({
      pilot: {
        count: "",
        average: "",
      },
      trial: {
        count: "",
        average: "",
      },
      formal: {
        count: "",
        average: "",
      },
    });

    // 获取讲师详细信息
    const fetchLecturerscore = async () => {
      if (!selectedLecturer.value) return;

      try {
        const response = await fetch(
          `api/lecturer-analysis/teachingscore?lecturer_name=${encodeURIComponent(
            selectedLecturer.value
          )}`
        );
        const lecturerscoreData = await response.json();
        // console.log("lecturerscoreData:", lecturerscoreData.data);
        if (lecturerscoreData.success && lecturerscoreData.data) {
          statisticsData.pilot.count = lecturerscoreData.data.pilot_count || 0;
          statisticsData.pilot.average = lecturerscoreData.data.pilot_avg || 0;

          statisticsData.trial.count = lecturerscoreData.data.trial_count || 0;
          statisticsData.trial.average = lecturerscoreData.data.trial_avg || 0;

          statisticsData.formal.count =
            lecturerscoreData.data.formal_count || 0;
          statisticsData.formal.average =
            lecturerscoreData.data.formal_avg || 0;
        } else {
          // 分数为空：保持置零
          statisticsData.pilot.count = 0;
          statisticsData.pilot.average = 0;
          statisticsData.trial.count = 0;
          statisticsData.trial.average = 0;
          statisticsData.formal.count = 0;
          statisticsData.formal.average = 0;
        }
      } catch (error) {
        console.error("获取讲师评分数据失败:", error);
        statisticsData.pilot.count = 0;
        statisticsData.pilot.average = 0;
        statisticsData.trial.count = 0;
        statisticsData.trial.average = 0;
        statisticsData.formal.count = 0;
        statisticsData.formal.average = 0;
      }
    };

    // 获取讲师图表数据
    const fetchLecturerChartData = async () => {
      if (!selectedLecturer.value) return;

      try {
        const response = await fetch(
          `/api/lecturer-analysis/teachingscore_line?lecturer_name=${encodeURIComponent(
            selectedLecturer.value
          )}`
        );
        const data = await response.json();

        if (data.success && data.data) {
          // 处理API数据并更新图表数据
          processChartData(data.data);

          // 如果图表已存在，先销毁再重新创建
          if (chart) {
            chart.dispose();
            chart = null;
          }

          // 等待下一个tick确保DOM更新
          await nextTick();
          // 重新渲染图表
          initChart();
        }
      } catch (error) {
        console.error("获取讲师图表数据失败:", error);
      }
    };

    // 计算分割线位置
    const calculateSeparatorLines = (teachingTypes) => {
      const separators = [];
      let lastTrialIndex = -1;
      let firstTestIndex = -1;
      let lastTestIndex = -1;
      let firstDeliveryIndex = -1;

      // 找到各阶段的边界位置
      teachingTypes.forEach((type, index) => {
        if (type.includes("試點")) {
          lastTrialIndex = index;
        } else if (type.includes("試跑")) {
          if (firstTestIndex === -1) {
            firstTestIndex = index;
          }
          lastTestIndex = index;
        } else if (type.includes("正式交付")) {
          if (firstDeliveryIndex === -1) {
            firstDeliveryIndex = index;
          }
        }
      });

      // 在最后一个試點和第一个試跑之间添加分割线
      if (
        lastTrialIndex !== -1 &&
        firstTestIndex !== -1 &&
        firstTestIndex > lastTrialIndex
      ) {
        const separatorPosition = lastTrialIndex + 0.5;
        // console.log(
        //   "分割线1位置:",
        //   separatorPosition,
        //   "试点结束:",
        //   lastTrialIndex,
        //   "试跑开始:",
        //   firstTestIndex
        // );
        separators.push({
          xAxis: separatorPosition,
        });
      }

      // 在最后一个試跑和第一个正式交付之间添加分割线
      if (
        lastTestIndex !== -1 &&
        firstDeliveryIndex !== -1 &&
        firstDeliveryIndex > lastTestIndex
      ) {
        const separatorPosition = lastTestIndex + 0.5;
        // console.log(
        //   "分割线2位置:",
        //   separatorPosition,
        //   "试跑结束:",
        //   lastTestIndex,
        //   "正式交付开始:",
        //   firstDeliveryIndex
        // );
        separators.push({
          xAxis: separatorPosition,
        });
      }

      // console.log("所有分割线:", separators);
      return separators;
    };

    // 生成阶段标签
    const generateStageLabels = (teachingTypes) => {
      const stages = [];
      let trialStart = -1,
        trialEnd = -1;
      let testStart = -1,
        testEnd = -1;
      let deliveryStart = -1,
        deliveryEnd = -1;

      // 找到各阶段的开始和结束位置
      teachingTypes.forEach((type, index) => {
        if (type.includes("試點")) {
          if (trialStart === -1) trialStart = index;
          trialEnd = index;
        } else if (type.includes("試跑")) {
          if (testStart === -1) testStart = index;
          testEnd = index;
        } else if (type.includes("正式交付")) {
          if (deliveryStart === -1) deliveryStart = index;
          deliveryEnd = index;
        }
      });

      // 添加阶段标签
      if (trialStart !== -1) {
        stages.push({
          coord: [(trialStart + trialEnd) / 2, 80],
          value: "試點階段",
          itemStyle: {
            color: "rgba(255, 255, 255, 0.9)",
          },
        });
      }

      if (testStart !== -1) {
        stages.push({
          coord: [(testStart + testEnd) / 2, 80],
          value: "試跑階段",
          itemStyle: {
            color: "rgba(255, 255, 255, 0.9)",
          },
        });
      }

      if (deliveryStart !== -1) {
        stages.push({
          coord: [(deliveryStart + deliveryEnd) / 2, 80],
          value: "正式交付階段",
          itemStyle: {
            color: "rgba(255, 255, 255, 0.9)",
          },
        });
      }

      return stages;
    };

    // 生成合格线数据
    const generateQualificationLines = (teachingTypes) => {
      // 第一条合格线：試點和試跑用90，正式交付用94
      const line1Data = [];
      const line2Data = [];

      teachingTypes.forEach((type) => {
        if (type.includes("試點")) {
          line1Data.push(90);
          line2Data.push(NaN);
        } else if (type.includes("正式交付") || type.includes("試跑")) {
          line1Data.push(NaN);
          line2Data.push(94);
        } else {
          line1Data.push(NaN);
          line2Data.push(NaN);
        }
      });

      // 新增逻辑：将第一个 NaN 修改为 90
      const firstNaNIndex = line1Data.findIndex((value) => isNaN(value));
      if (firstNaNIndex !== -1) {
        line1Data[firstNaNIndex] = 90;
      }
      return [
        {
          name: "合格線",
          type: "line",
          data: line1Data,
          itemStyle: {
            color: "#C00000",
          },
          lineStyle: {
            color: "#C00000",
            width: 2,
            type: "dashed",
          },
          symbol: "none",
          connectNulls: false,
          z: 1, // 确保合格线在数据线下方
        },
        {
          name: "合格線",
          type: "line",
          data: line2Data,
          itemStyle: {
            color: "#C00000",
          },
          lineStyle: {
            color: "#C00000",
            width: 2,
            type: "dashed",
          },
          symbol: "none",
          connectNulls: false,
          z: 1, // 确保合格线在数据线下方
        },
      ];
    };

    // 生成左右兩端標註文本（左90，右94），以散點系列形式加入，不影響 tooltip 與圖例
    const generateEdgeLabelSeries = (teachingTypes) => {
      if (!Array.isArray(teachingTypes) || teachingTypes.length === 0)
        return null;
      const first = teachingTypes[0];
      const last = teachingTypes[teachingTypes.length - 1];

      const common = {
        name: "合格線標註",
        type: "scatter",
        symbolSize: 1,
        itemStyle: { color: "#C00000" },
        tooltip: { show: false },
        emphasis: { disabled: true },
        z: 10,
        silent: true,
      };

      // 左側 90（標註顯示在點的左側）
      const leftSeries = {
        ...common,
        data: [[first, 90]],
        label: {
          show: true,
          formatter: (p) => String(p.data[1]),
          position: "left",
          offset: [-20, 0],
          color: "#C00000",
          fontSize: 14,
          fontWeight: "bold",
        },
      };

      // 右側 94（標註顯示在點的右側）
      const rightSeries = {
        ...common,
        data: [[last, 94]],
        label: {
          show: true,
          formatter: (p) => String(p.data[1]),
          position: "right",
          offset: [20, 0],
          color: "#C00000",
          fontSize: 14,
          fontWeight: "bold",
        },
      };

      return [leftSeries, rightSeries];
    };

    // 处理图表数据
    const processChartData = (apiData) => {
      // 收集所有的teaching_type并排序
      const allTeachingTypes = new Set();
      apiData.forEach((courseData) => {
        courseData.new_teaching_type?.forEach((type) => {
          allTeachingTypes.add(type);
        });
      });

      // 按照試點、試跑、正式交付的顺序排序
      const sortedTeachingTypes = Array.from(allTeachingTypes).sort((a, b) => {
        const getOrder = (type) => {
          if (type.includes("試點")) return 1;
          if (type.includes("試跑")) return 2;
          if (type.includes("正式交付")) return 3;
          return 4;
        };

        const getNumber = (type) => {
          const match = type.match(/\d+/);
          return match ? parseInt(match[0]) : 0;
        };

        const orderA = getOrder(a);
        const orderB = getOrder(b);

        if (orderA !== orderB) {
          return orderA - orderB;
        }

        return getNumber(a) - getNumber(b);
      });

      // 更新X轴标签
      chartData.xAxisLabels = sortedTeachingTypes;
      // console.log("X轴标签:", chartData.xAxisLabels);

      // 生成合格线数据
      const qualificationLines =
        generateQualificationLines(sortedTeachingTypes);

      // 生成左右端標註（左90/右94）
      const edgeLabelSeries = generateEdgeLabelSeries(sortedTeachingTypes);

      // 计算分割线位置
      chartData.separatorLines = calculateSeparatorLines(sortedTeachingTypes);
      // console.log("分割线数据:", chartData.separatorLines);

      // 生成阶段标签
      chartData.stageLabels = generateStageLabels(sortedTeachingTypes);

      // 处理每个课程的数据
      chartData.dynamicSeries = apiData.map((courseData, index) => {
        const courseName = courseData.course_name;
        const teachingTypes = courseData.new_teaching_type || [];
        const teachingScores = courseData.teaching_score || [];

        // 创建一个映射，将teaching_type和对应的score关联
        const scoreMap = {};
        teachingTypes.forEach((type, idx) => {
          if (idx < teachingScores.length) {
            scoreMap[type] = teachingScores[idx];
          }
        });

        // 根据排序后的teaching_type创建数据数组
        const seriesData = sortedTeachingTypes.map((type) => {
          return scoreMap[type] || null; // 如果没有对应的分数，设为null
        });

        // 定义颜色数组
        const colors = [
          "#FF0000",
          "#FF7F00",
          "#FFFF00",
          "#00FF00",
          "#00FFFF",
          "#0000FF",
          "#8B00FF",
          "#FF00FF",
        ];

        return {
          name: courseName,
          type: "line",
          data: seriesData,
          lineStyle: {
            color: colors[index % colors.length],
            width: 3,
          },
          // 标签样式：微调并使用 labelLayout 避免重叠
          label: {
            show: true,
            // 根据系列索引交替显示在上方或下方，减小同 x 值堆叠概率
            // position: function (params) {
            //   return params.seriesIndex % 2 === 0 ? "top" : "bottom";
            // },
            position: "top",
            color: "#000",
            fontSize: 12,
            // 智能隐藏过于接近的标签：如果同一 x 上存在比当前 series 索引更小且差值很小的点，则隐藏当前标签
            formatter: function (params) {
              const val = params.value;
              if (val === null || val === undefined || isNaN(val)) return "";

              try {
                // 只比较课程系列（排除合格线等辅助序列）
                const courseSeries = chartData.dynamicSeries.filter(
                  (s) => !s.name.includes("合格線") && s.type === "line"
                );

                // 找到当前系列在 courseSeries 中的位置（按 name 匹配）
                const curIndex = courseSeries.findIndex(
                  (s) => s.name === params.seriesName
                );

                // 如果没找到则直接显示
                if (curIndex === -1) {
                  return parseFloat(val).toFixed(2);
                }

                const dataIndex = params.dataIndex;
                const threshold = 0.5; // 可调：差值小于该阈值视为接近

                // 遍历当前系列之前的课程系列，只要存在一个更早的系列在此 x 上数值接近，则隐藏当前系列的标签
                for (let i = 0; i < curIndex; i++) {
                  const otherVal = courseSeries[i].data[dataIndex];
                  if (
                    otherVal !== null &&
                    otherVal !== undefined &&
                    !isNaN(otherVal) &&
                    Math.abs(parseFloat(otherVal) - parseFloat(val)) < threshold
                  ) {
                    return ""; // 隐藏当前标签，优先保留序号小的系列标签
                  }
                }

                return parseFloat(val).toFixed(2);
              } catch (e) {
                // 出错时回退为默认格式
                return parseFloat(params.value).toFixed(2);
              }
            },
            // distance: 8,
            // padding: [2, 8],
            // // 使用半透明背景提高可读性（可按需移除）
            // backgroundColor: "rgba(255,255,255,0.8)",
            // borderRadius: 4,
          },
          labelLayout: {
            // 当标签重合时优先移动以避免遮挡
            hideOverlap: true,
            // 在 Y 方向上移动以错开重叠标签
            moveOverlap: "shiftY",
          },
          itemStyle: {
            color: colors[index % colors.length],
            borderWidth: 2,
            borderColor: "#ffffff",
          },
          symbol: "circle",
          symbolSize: 6,
          smooth: true,
          emphasis: {
            focus: "series",
          },
          connectNulls: true, // 不连接null值的点
        };
      });

      // 将合格线添加到系列数据中
      chartData.dynamicSeries = [
        ...chartData.dynamicSeries,
        ...qualificationLines,
        ...(edgeLabelSeries ? edgeLabelSeries : []),
      ];
    };

    // 图表数据 - 动态生成
    const chartData = {
      xAxisLabels: [], // X轴标签（教学类型）
      dynamicSeries: [], // 动态生成的系列数据
      separatorLines: [], // 分割线数据
      stageLabels: [], // 阶段标签数据
    };

    // 初始化图表
    const initChart = () => {
      if (!chartContainer.value) return;

      // 如果图表已存在，先销毁
      if (chart) {
        chart.dispose();
        chart = null;
      }

      chart = echarts.init(chartContainer.value);

      // 计算Y轴的最小值和最大值
      let minScore = 80; // 确保包含阶段标签空间
      let maxScore = 100;

      if (chartData.dynamicSeries.length > 0) {
        // 只考虑课程数据，不考虑合格线数据
        const courseDataScores = chartData.dynamicSeries
          .filter((series) => !series.name.includes("合格線"))
          .flatMap((series) =>
            series.data.filter((score) => score !== null && !isNaN(score))
          );

        if (courseDataScores.length > 0) {
          const minDataScore = Math.min(...courseDataScores);
          const maxDataScore = Math.max(...courseDataScores);

          // 考虑合格线分数 (90, 94)
          // minScore = Math.max(82, Math.min(minDataScore, 90) - 3);
          // maxScore = Math.min(102, Math.max(maxDataScore, 94) + 2);
        } else {
          // 如果没有课程数据，使用默认范围包含合格线
          minScore = 85;
          maxScore = 100;
        }
      }

      const option = {
        backgroundColor: "transparent",
        grid: {
          left: "3%",
          right: "3%",
          top: "20%",
          bottom: "5%",
          containLabel: true,
        },
        xAxis: {
          type: "category",
          data: chartData.xAxisLabels,
          axisPointer: { label: { show: false } },
          axisLabel: {
            formatter: function (value) {
              // 使用正则表达式分割：保留连续数字和字母，非数字字母拆分并加换行
              return value
                .replace(
                  /([a-zA-Z0-9]+)|([^a-zA-Z0-9])/g,
                  (matched, alphanum, nonAlphanum) => {
                    if (alphanum) {
                      return `${alphanum}`; // 数字和字母保留整体
                    } else if (nonAlphanum) {
                      return `${nonAlphanum}\n`; // 非数字字母拆分并加换行
                    }
                    return matched;
                  }
                )
                .trim();
            },
            rotate: 0, // 标签逆时针旋转45度
            interval: 0, // 强制显示所有标签（避免自动隐藏）
            color: "#000",
            fontSize: 14,
            //   margin: 15, // 标签与轴线间距
            //   inside: false, // 标签显示在轴线外侧
          },
          axisLine: {
            lineStyle: {
              color: "rgba(0,0,0,0.3)",
            },
          },
          // axisTick: {
          //   lineStyle: {
          //     color: "rgba(255, 255, 255, 0.3)",
          //   },
          // },
        },
        yAxis: {
          type: "value",
          min: minScore,
          max: maxScore,
          interval: (maxScore - minScore) / 5, // 设置固定的刻度间隔，分为5段
          axisPointer: { label: { show: false } },
          axisLabel: {
            color: "#000000",
            fontSize: 13,
            formatter: "{value}",
          },
          axisLine: {
            lineStyle: {
              color: "#C00000",
            },
          },
          // 水平网格线：更明显的实线风格，接近示例效果
          splitLine: {
            show: true,
            lineStyle: {
              // 更明显的浅灰/蓝色线条（可根据页面背景微调）
              color: "rgba(0, 0, 0, 0.08)",
              width: 1,
              type: "solid",
            },
          },
          // 交替背景色：轻微的条带增强行对齐感（颜色偏向白/浅蓝，可按需调整）
          splitArea: {
            show: true,
            areaStyle: {
              color: ["rgba(255,255,255,0.00)", "rgba(240,248,255,0.02)"],
            },
          },
        },
        series: [
          ...chartData.dynamicSeries,
          // 添加一个隐藏的系列专门用于显示分割线
          {
            name: "阶段分割线",
            type: "line",
            data: chartData.xAxisLabels.map(() => null),
            lineStyle: { opacity: 0 },
            symbol: "none",
            silent: true,
            markLine: {
              symbol: "none",
              lineStyle: {
                color: "rgba(0, 0, 0, 0.8)",
                width: 2,
                type: "dashed",
              },
              label: {
                show: false,
              },
              data: chartData.separatorLines.map((line) => ({
                xAxis: line.xAxis,
                lineStyle: {
                  color: "rgba(0, 0, 0, 0.8)",
                  width: 2,
                  type: "dashed",
                },
              })),
            },
          },
        ],
        // 添加图表标记
        graphic: [
          // 添加阶段标签
          ...chartData.stageLabels.map((label) => ({
            type: "text",
            left: `${
              ((label.coord[0] + 0.5) / chartData.xAxisLabels.length) * 100
            }%`,
            top: "15%",
            style: {
              text: label.value,
              fill: "rgba(0, 0, 0, 0.9)",
              fontSize: 16,
              fontWeight: "bold",
              textAlign: "center",
            },
          })),
        ],
        tooltip: {
          trigger: "axis",
          backgroundColor: "rgba(255,255,255,0.5)",
          borderColor: "rgba(0,0,0,0.2)",
          borderWidth: 1,
          textStyle: {
            color: "#000000",
          },
          axisPointer: {
            type: "cross",
            label: { show: false },
            crossStyle: {
              color: "rgba(255,255,255,0.5)",
            },
          },
          formatter: function (params) {
            let result = `${params[0].axisValue}<br/>`;
            params.forEach((param) => {
              // 只显示课程数据，不显示合格线
              if (
                param.value !== null &&
                param.value !== undefined &&
                !param.seriesName.includes("合格線")
              ) {
                result += `<span style="display:inline-block;margin-right:5px;border-radius:10px;width:10px;height:10px;background-color:${param.color};"></span>${param.seriesName}: ${param.value}<br/>`;
              }
            });

            // 显示对应的合格线标准
            // const currentType = params[0].axisValue;
            // if (currentType.includes("試點") || currentType.includes("試跑")) {
            //   result += `<span style="color:#ff6b6b;">合格標準: 90</span>`;
            // } else if (currentType.includes("正式交付")) {
            //   result += `<span style="color:#ff6b6b;">合格標準: 94</span>`;
            // }

            return result;
          },
        },
        legend: {
          textStyle: {
            color: "#000",
            fontSize: 13,
          },
          right: "5%",
          top: "3%",
          type: "scroll", // 如果图例过长，支持滚动
          // 过滤图例数据，排除分割线，合并合格线为单个图例
          data: (() => {
            const legendData = chartData.dynamicSeries
              .filter(
                (series) =>
                  !series.name.includes("合格線") &&
                  !series.name.includes("分割线") &&
                  !series.name.includes("阶段分割线")
              )
              .map((series) => series.name);

            // 添加统一的合格线图例
            const hasQualificationLine = chartData.dynamicSeries.some(
              (series) => series.name.includes("合格線")
            );

            if (hasQualificationLine) {
              legendData.push("合格線");
            }

            return legendData;
          })(),
        },
      };

      chart.setOption(option);

      // 添加图例选择事件监听
      chart.on("legendselectchanged", (params) => {
        if (params.name === "合格線") {
          // 控制所有合格线系列的显示/隐藏
          const qualificationSeries = chartData.dynamicSeries.filter((series) =>
            series.name.includes("合格線")
          );

          qualificationSeries.forEach((series) => {
            const seriesName = series.name;
            const action = params.selected["合格線"]
              ? "showSeries"
              : "hideSeries";
            chart.dispatchAction({
              type: action,
              seriesName: seriesName,
            });
          });
        }
      });

      // 创建 resize 处理函数（如果还没有创建）
      if (!resizeHandler) {
        resizeHandler = () => {
          if (chart) {
            chart.resize();
          }
        };
        // 只绑定一次 resize 事件
        window.addEventListener("resize", resizeHandler);
      }
    };

    // 导出功能
    const handleExport = async () => {
      if (!selectedLecturer.value) {
        ElMessage({ message: "請先選擇講師", type: "warning", duration: 2000 });
        return;
      }
      try {
        ElMessage({
          message: `正在導出講師的分析數據...`,
          type: "info",
          duration: 2000,
        });
        const resp = await fetch(
          `/api/lecturer-analysis/export?lecturer_name=${encodeURIComponent(
            selectedLecturer.value
          )}&export_csv=true&keep=false`
        );
        if (!resp.ok) throw new Error(`HTTP error ${resp.status}`);
        const data = await resp.json();
        if (data.success && data.file && data.file.url) {
          const a = document.createElement("a");
          a.href = data.file.url;
          a.download =
            data.file.name ||
            `講師分析_${selectedLecturer.value}_${timestamp}.csv`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          ElMessage({ message: "導出成功", type: "success", duration: 2000 });
        } else {
          throw new Error(data.message || "未獲取到文件URL");
        }
      } catch (e) {
        console.error("导出失败:", e);
        ElMessage({
          message: "導出失敗，請稍後重試",
          type: "error",
          duration: 3000,
        });
      }
    };

    // 照片URL处理方法
    const getPhotoUrl = (photoUrl) => {
      if (!photoUrl) return "";
      if (photoUrl.startsWith("http://") || photoUrl.startsWith("https://")) {
        return photoUrl;
      }
      return photoUrl.startsWith("/") ? photoUrl : `/${photoUrl}`;
    };

    // 图片加载错误处理
    const handleImageError = (event) => {
      // console.warn("图片加载失败:", lecturerInfo.photoUrl);
      // 图片加载失败时，清空photoUrl，这样会显示占位符
      lecturerInfo.photoUrl = "";
      ElMessage({
        message: "圖片加載失敗",
        type: "warning",
        duration: 2000,
      });
    };

    // 图片加载成功处理
    const handleImageLoad = (event) => {
      // console.log("图片加载成功:", lecturerInfo.photoUrl);
    };

    // 照片上传相关方法
    const triggerFileUpload = () => {
      if (!selectedLecturer.value) {
        ElMessage({
          message: "請先選擇講師",
          type: "warning",
          duration: 2000,
        });
        return;
      }
      fileInput.value.click();
    };

    const handleFileUpload = async (event) => {
      const file = event.target.files[0];
      if (!file) return;

      // 文件类型验证
      if (!file.type.startsWith("image/")) {
        ElMessage({
          message: "請選擇圖片文件（JPG、PNG、GIF等）",
          type: "error",
          duration: 2000,
        });
        return;
      }

      // 文件大小验证 (限制为5MB)
      if (file.size > 5 * 1024 * 1024) {
        ElMessage({
          message: "圖片大小不能超過5MB",
          type: "error",
          duration: 2000,
        });
        return;
      }

      try {
        uploading.value = true;

        // 创建FormData对象
        const formData = new FormData();
        formData.append("photo", file);
        formData.append("lecturer_name", selectedLecturer.value);

        // 上传照片到服务器
        const response = await fetch("/api/lecturer-analysis/upload-photo", {
          method: "POST",
          body: formData,
        });
        console.log("上传响应:", response);
        const result = await response.json();

        if (response.ok && result.success) {
          // 更新照片URL
          lecturerInfo.photoUrl = result.data.photo_url;
          ElMessage({
            message: "照片上傳成功",
            type: "success",
            duration: 2000,
          });
        } else {
          throw new Error(result.message || `服务器错误: ${response.status}`);
        }
      } catch (error) {
        console.error("照片上传失败:", error);
        let errorMessage = "照片上傳失敗，請稍後重試";

        // 根据错误类型显示不同消息
        if (error.message.includes("只能上传图片文件")) {
          errorMessage = "只能上傳圖片文件";
        } else if (error.message.includes("讲师不存在")) {
          errorMessage = "講師不存在";
        } else if (error.message.includes("没有上传文件")) {
          errorMessage = "請選擇要上傳的文件";
        }

        ElMessage({
          message: errorMessage,
          type: "error",
          duration: 3000,
        });
      } finally {
        uploading.value = false;
        // 清空文件输入，允许重复选择同一文件
        event.target.value = "";
      }
    };

    const removePhoto = async () => {
      try {
        const result = await ElMessageBox.confirm(
          "確定要刪除這張照片嗎？",
          "確認刪除",
          {
            confirmButtonText: "確定",
            cancelButtonText: "取消",
            type: "warning",
          }
        );

        if (result === "confirm") {
          // 调用删除API
          const response = await fetch("/api/lecturer-analysis/delete-photo", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              lecturer_name: selectedLecturer.value,
            }),
          });

          const apiResult = await response.json();

          if (response.ok && apiResult.success) {
            lecturerInfo.photoUrl = "";
            ElMessage({
              message: "照片刪除成功",
              type: "success",
              duration: 2000,
            });
          } else {
            let errorMessage = "刪除照片失敗，請稍後重試";

            // 根据错误类型显示不同消息
            if (apiResult.message.includes("讲师不存在")) {
              errorMessage = "講師不存在";
            } else if (apiResult.message.includes("没有上传照片")) {
              errorMessage = "該講師沒有上傳照片";
            }

            throw new Error(errorMessage);
          }
        }
      } catch (error) {
        if (error !== "cancel") {
          console.error("删除照片失败:", error);
          ElMessage({
            message: error.message || "刪除照片失敗，請稍後重試",
            type: "error",
            duration: 3000,
          });
        }
      }
    };

    // 返回按钮功能
    const goBack = () => {
      // 如果有课程参数，返回到教学记录页面并传递课程参数
      const courseParam = route.query.course;
      if (courseParam) {
        router.push({
          name: "TeachingRecord",
          query: { course: courseParam },
        });
      } else {
        // 否则返回上一页
        router.go(-1);
      }
    };

    // 刷新功能
    const refreshPage = async () => {
      if (refreshing.value || loading.value) return;

      refreshing.value = true;
      try {
        // 重新加载讲师选项数据
        await fetchLecturerOptions();

        // 如果有选中的讲师，重新加载相关数据
        if (selectedLecturer.value) {
          await fetchLecturerData();
        }

        ElMessage({
          message: "刷新成功",
          type: "success",
          duration: 1500,
        });
      } catch (error) {
        console.error("刷新失败:", error);
        ElMessage({
          message: "刷新失败",
          type: "error",
          duration: 2000,
        });
      } finally {
        refreshing.value = false;
      }
    };

    // 组件挂载后初始化图表和获取数据
    onMounted(async () => {
      // 先获取讲师选项数据
      await fetchLecturerOptions();

      // 如果有选中的讲师，获取相关数据
      if (selectedLecturer.value) {
        await fetchLecturerData();
      }

      // 然后初始化图表
      nextTick(() => {
        initChart();
      });
    });

    // 组件卸载时清理图表
    onUnmounted(() => {
      if (chart) {
        chart.dispose();
        chart = null;
      }
      // 移除窗口resize监听器
      if (resizeHandler) {
        window.removeEventListener("resize", resizeHandler);
        resizeHandler = null;
      }
    });

    // 监听讲师名称变化
    watch(
      () => route.query.lecturer,
      (newLecturer) => {
        selectedLecturer.value = newLecturer;
        if (newLecturer) {
          fetchLecturerData();
        }
      }
    );

    return {
      selectedLecturer,
      lecturerFromParams,
      lecturerOptions,
      lecturerInfo,
      statisticsData,
      chartContainer,
      refreshing,
      loading,
      fileInput,
      uploading,
      handleExport,
      handleNameChange,
      goBack,
      refreshPage,
      triggerFileUpload,
      handleFileUpload,
      removePhoto,
      getPhotoUrl,
      handleImageError,
      handleImageLoad,
      clearLecturerData,
    };
  },
};
</script>

<style scoped>
@import "@/style/general.css";

.placeholder {
  flex: 0 0 auto;
  width: 120px; /* 与返回按钮宽度保持平衡 */
}

@keyframes titleGlow {
  0% {
    text-shadow: 0 4px 8px rgba(0, 0, 0, 0.4), 0 0 20px rgba(59, 130, 246, 0.3);
  }
  100% {
    text-shadow: 0 4px 12px rgba(0, 0, 0, 0.6), 0 0 30px rgba(147, 51, 234, 0.5),
      0 0 40px rgba(16, 185, 129, 0.3);
  }
}

@keyframes gradientShift {
  0% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0% 50%;
  }
}

@keyframes fadeInDown {
  0% {
    opacity: 0;
    transform: translateY(-20px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

.export-info {
  position: absolute;
  right: 10px;
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

.export-btn::before {
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

.export-btn:hover::before {
  left: 100%;
}

/* .export-btn:hover {
  background: linear-gradient(45deg, #059669, #047857);
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(16, 185, 129, 0.4);
} */

.export-btn .el-icon {
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.course-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin-bottom: 15px;
  padding: 0 10px;
  position: relative;
  flex-shrink: 0;
}

.header-controls {
  display: flex;
  align-items: center;
}

.lecturer-select {
  width: 150px;
}

:deep(.lecturer-select .el-input__inner) {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: white;
}

:deep(.lecturer-select .el-input__inner::placeholder) {
  color: rgba(255, 255, 255, 0.6);
}

/* 主要内容区域 */
.content {
  display: flex;
  gap: 30px;
  margin-bottom: 50px;
  padding-left: 80px;
}

/* 左侧讲师信息区域 */
.lecturer-info-section {
  flex: 1;
  display: flex;
  gap: 30px;
}

.lecturer-photo {
  width: 250px;
  height: 300px;
  position: relative;
}

.photo-container {
  width: 100%;
  height: 100%;
  border-radius: 15px;
  overflow: hidden;
  cursor: pointer;
  position: relative;
  transition: all 0.3s ease;
}

.photo-container:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
}

.lecturer-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 15px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  transition: all 0.3s ease;
}

.lecturer-image:hover {
  border-color: rgba(59, 130, 246, 0.5);
}

/* 图片加载失败时的样式 */
.lecturer-image:error {
  display: none;
}

.photo-placeholder {
  width: 100%;
  height: 100%;
  background: linear-gradient(
    145deg,
    rgba(255, 255, 255, 0.15),
    rgba(255, 255, 255, 0.05)
  );
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 15px;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(15px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
  position: relative;
  overflow: hidden;
  transition: all 0.3s ease;
}

.placeholder-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  color: rgba(255, 255, 255, 0.7);
  z-index: 2;
  position: relative;
}

.upload-icon {
  font-size: 32px;
  opacity: 0.8;
}

.placeholder-text {
  font-size: 14px;
  font-weight: 500;
}

.upload-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: white;
  border-radius: 15px;
  z-index: 10;
}

.loading-icon {
  font-size: 24px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.photo-placeholder::before {
  content: "";
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: conic-gradient(
    from 0deg,
    transparent,
    rgba(59, 130, 246, 0.1),
    transparent,
    rgba(147, 51, 234, 0.1),
    transparent
  );
  animation: rotate 8s linear infinite;
}

.photo-placeholder:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.3);
  border-color: rgba(59, 130, 246, 0.5);
}

.photo-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  margin-bottom: 10px;
  justify-content: center;
}

.action-btn {
  flex: 1;
  font-size: 12px;
  padding: 6px 12px;
  border-radius: 6px;
}

.action-btn.el-button--primary {
  background: linear-gradient(45deg, #129cd6, #0ea5d6);
  border-color: #129cd6;
}

.action-btn.el-button--primary:hover {
  background: linear-gradient(45deg, #0ea5d6, #0c94c4);
  transform: translateY(-1px);
}

.action-btn.el-button--danger {
  background: linear-gradient(45deg, #ff6b6b, #ff5252);
  border-color: #ff6b6b;
}

.action-btn.el-button--danger:hover {
  background: linear-gradient(45deg, #ff5252, #f44336);
  transform: translateY(-1px);
}

@keyframes rotate {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.lecturer-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-left: 100px;
}

.info-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.info-label {
  color: #000000;
  font-size: 20px;
  font-weight: bold;
  white-space: nowrap;
  min-width: 100px;
}

.info-value {
  color: #000000;
  font-size: 20px;
  flex: 1;
}

/* 右侧统计信息区域 */
.statistics-section {
  width: 550px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.stats-grid {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.stat-card {
  background: linear-gradient(
    145deg,
    rgba(255, 255, 255, 0.15),
    rgba(255, 255, 255, 0.08)
  );
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 15px;
  padding: 20px 25px;
  display: flex;
  align-items: center;
  gap: 15px;
  backdrop-filter: blur(20px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.2), inset 0 -1px 0 rgba(0, 0, 0, 0.1);
  position: relative;
  overflow: hidden;
  transition: all 0.3s ease;
}

.stat-card::before {
  content: "";
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.1),
    transparent
  );
  transition: left 0.5s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.3), 0 0 20px rgba(59, 130, 246, 0.2);
  border-color: rgba(59, 130, 246, 0.4);
}

.stat-card:hover::before {
  left: 100%;
}

.stat-label {
  color: #000000;
  font-size: 16px;
  white-space: nowrap;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  min-width: 30px;
}

.stat-average {
  color: #ffffff;
  font-size: 14px;
}

.red {
  color: #e44904;
}

.export-section {
  display: flex;
  justify-content: flex-end;
}

.export-btn {
  background: linear-gradient(45deg, #3875c5, #3875c5);
  border: none;
  padding: 12px 30px;
  font-size: 16px;
  border-radius: 8px;
  color: white;
  font-weight: bold;
  box-shadow: 0 4px 15px rgba(18, 156, 214, 0.3);
  transition: all 0.3s ease;
}

.export-btn:hover {
  background: linear-gradient(45deg, #3875c5, #3875c5);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(18, 156, 214, 0.4);
}

/* 图表区域 */
.chart-section {
  background: linear-gradient(
    145deg,
    rgba(255, 255, 255, 0.12),
    rgba(255, 255, 255, 0.06)
  );
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 20px;
  padding: 30px;
  backdrop-filter: blur(20px);
  margin-top: 20px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.2), inset 0 -1px 0 rgba(0, 0, 0, 0.1);
  position: relative;
  overflow: hidden;
}

.chart-section::before {
  content: "";
  position: absolute;
  top: -2px;
  left: -2px;
  right: -2px;
  bottom: -2px;
  background: linear-gradient(
    45deg,
    rgba(59, 130, 246, 0.3),
    rgba(147, 51, 234, 0.3),
    rgba(16, 185, 129, 0.3),
    rgba(59, 130, 246, 0.3)
  );
  border-radius: 20px;
  z-index: -1;
  animation: borderGlow 3s linear infinite;
}

@keyframes borderGlow {
  0%,
  100% {
    opacity: 0.5;
  }
  50% {
    opacity: 1;
  }
}

.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 30px;
  padding: 0 10px;
}

.chart-title {
  color: #ffffff;
  font-size: 22px;
  font-weight: bold;
  margin: 0;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.legend-section {
  display: flex;
  gap: 20px;
  align-items: center;
  flex-wrap: wrap;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.3s ease;
}

.legend-item:hover {
  background: rgba(255, 255, 255, 0.15);
  border-color: rgba(255, 255, 255, 0.3);
  transform: translateY(-1px);
}

.legend-color {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.legend-text {
  color: #ffffff;
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
}

.main-chart {
  height: 450px;
  width: 100%;
  /*background: linear-gradient(145deg, rgba(0, 0, 0, 0.15), rgba(0, 0, 0, 0.08));*/
  border-radius: 15px;
  border: 1px solid rgba(0, 0, 0);
  backdrop-filter: blur(10px);
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.1),
    inset 0 -2px 4px rgba(255, 255, 255, 0.05);
  position: relative;
  overflow: hidden;
}

.main-chart::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(
      circle at 30% 20%,
      rgba(59, 130, 246, 0.05) 0%,
      transparent 50%
    ),
    radial-gradient(
      circle at 70% 80%,
      rgba(147, 51, 234, 0.03) 0%,
      transparent 50%
    );
  pointer-events: none;
}

/* Element Plus 组件样式覆盖 */
:deep(.el-select-dropdown) {
  background: rgba(30, 58, 138, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(10px);
}

:deep(.el-select-dropdown .el-select-dropdown__item) {
  color: white;
}

:deep(.el-select-dropdown .el-select-dropdown__item:hover) {
  background: rgba(255, 255, 255, 0.1);
}

:deep(.el-select-dropdown .el-select-dropdown__item.selected) {
  background: rgba(18, 156, 214, 0.3);
  color: white;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .content {
    flex-direction: column;
  }

  .statistics-section {
    width: 100%;
  }

  .stats-grid {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .stat-card {
    flex: 1;
    min-width: 200px;
  }
}

@media (max-width: 768px) {
  .lecturer-info-section {
    flex-direction: column;
  }

  .lecturer-photo {
    width: 100%;
    height: 200px;
  }

  .chart-container {
    flex-direction: column;
    gap: 20px;
  }

  .legend-section {
    width: 100%;
    flex-direction: row;
    flex-wrap: wrap;
    justify-content: center;
  }
}
</style>
