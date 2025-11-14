<template>
  <div class="dashboard-container">
    <div class="header">
      <h1>翰林院-品保</h1>
    </div>
    <div class="top-nav">
      <div class="back-section">
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
      <div class="export-info">
        <el-button type="primary" class="export-btn" @click="handleExport">
          <!-- <el-icon><Download /></el-icon> -->
          導出
        </el-button>
      </div>
    </div>

    <!-- 主要内容区域 -->
    <div class="content">
      <!-- 上半部分：进度折线图 -->
      <div class="top-section">
        <div class="chart-container full-width">
          <!-- 课程标题和状态筛选 -->
          <div class="course-header">
            <h3 class="course-title">課程《{{ courseName }}》</h3>
            <div class="status-filter">
              <el-select
                v-model="selectedStatus"
                @change="handleCourseChange"
                :placeholder="courseName"
                class="status-select"
                filterable
                clearable
              >
                <el-option
                  v-for="option in courseOptions"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                ></el-option>
              </el-select>
            </div>
          </div>
          <div class="chart-wrapper">
            <v-chart class="progress-chart" :option="progressChartOption" />
            <div class="progress-stats">
              <div class="stat-item">
                <span class="stat-number">{{ totalTrial }}</span>
                <span class="stat-label">試點</span>
              </div>
              <div class="stat-item">
                <span class="stat-number">{{ totalTest }}</span>
                <span class="stat-label">試跑</span>
              </div>
              <div class="stat-item">
                <span class="stat-number">{{ totalDelivery }}</span>
                <span class="stat-label">正式交付</span>
              </div>
              <div class="stat-item">
                <span class="stat-number">{{ totalAverage }}</span>
                <span class="stat-label">正式交付平均分</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 下半部分：左侧柱状图 + 右侧教师数据 -->
      <div class="bottom-section">
        <!-- 左侧1/4：厂区统计柱状图 -->
        <div class="left-quarter">
          <div class="factory-stats">
            <v-chart class="factory-chart" :option="factoryChartOption" />
          </div>
        </div>

        <!-- 右侧3/4：教师状态表格 -->
        <div class="right-three-quarters">
          <div class="table-header">BY戰區講師狀況</div>

          <div class="legend-bar">
            <div class="legend-item completed">
              <span class="legend-dot"></span>
              <span>資格認定達標</span>
            </div>
            <div class="legend-item pending">
              <span class="legend-dot"></span>
              <span>待資格認定</span>
            </div>
          </div>

          <!-- 教师状态表格 - 三个横向表格 -->
          <div class="teacher-tables-container">
            <div
              class="region-table"
              v-for="region in regionTableData"
              :key="region.name"
            >
              <!-- 表格头部 - 楼层标题 -->
              <div class="table-header-row">
                <div
                  class="floor-header-cell"
                  v-for="floor in region.floors"
                  :key="floor.floor"
                >
                  {{ floor.floor }}
                </div>
              </div>

              <!-- 表格数据行 -->
              <div class="table-body">
                <div
                  class="table-row"
                  v-for="rowIndex in getMaxTeachersInFloor(region)"
                  :key="`row-${rowIndex}`"
                >
                  <div
                    v-for="floor in region.floors"
                    :key="`${floor.floor}-${rowIndex}`"
                    :class="getTeacherCellClass(floor.teachers[rowIndex - 1])"
                  >
                    <div
                      v-if="floor.teachers[rowIndex - 1]"
                      class="teacher-info"
                      @click="
                        goToLecturerAnalysis(floor.teachers[rowIndex - 1])
                      "
                    >
                      <div class="teacher-name">
                        {{ floor.teachers[rowIndex - 1].name }}
                      </div>
                      <div
                        class="teacher-score"
                        v-if="floor.teachers[rowIndex - 1].qualified"
                      >
                        {{ floor.teachers[rowIndex - 1].score }}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 地区名称标签 -->
              <div class="region-label">{{ region.name }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch, nextTick } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";

const route = useRoute();
const router = useRouter();
const selectedStatus = ref("");
const courseOptions = ref([]);
const refreshing = ref(false);
const loading = ref(false);

// 生成时间戳用于文件命名
const now = new Date();
const pad = (n) => n.toString().padStart(2, "0");
const timestamp = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(
  now.getDate()
)}${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;

// 计算属性获取当前课程
const courseName = computed(() => route.query.course || "");

// 获取课程选项
const fetchCourseOptions = async () => {
  try {
    const response = await fetch("api/teaching-record/course-name-options");
    const data = await response.json();
    courseOptions.value = data.Options || [];
  } catch (error) {
    console.error("获取课程选项失败:", error);
    ElMessage.error("获取课程选项失败");
  }
};

// 处理课程变更
const handleCourseChange = (courseValue) => {
  router.push({ query: { ...route.query, course: courseValue } });
  // 延迟执行确保路由更新完成
  nextTick(() => {
    Promise.all([
      fetchTeachingRecords(),
      fetchFactoryData(),
      fetchTeacherGroupData(),
    ]);
  });
};

// 获取教学记录数据
const fetchTeachingRecords = async () => {
  if (!courseName.value) return;

  try {
    loading.value = true;
    const response = await fetch(
      `api/teaching-record/line_coursename?course_name_value=${encodeURIComponent(
        courseName.value
      )}`
    );
    const result = await response.json();

    if (result.success && result.data) {
      updateChartData(result.data);
      updateStatistics(result.data);
    } else {
      ElMessage.error("获取教学记录数据失败");
    }
  } catch (error) {
    console.error("获取教学记录失败:", error);
    ElMessage.error("获取教学记录失败");
  } finally {
    loading.value = false;
  }
};

// 获取厂区统计数据
const fetchFactoryData = async () => {
  if (!courseName.value) return;

  try {
    const response = await fetch(
      `api/teaching-record/bar_coursename?course_name_value=${encodeURIComponent(
        courseName.value
      )}`
    );
    const result = await response.json();

    // console.log("厂区API响应:", result); // 调试日志

    if (result.success && result.data) {
      // 检查数据格式：对象包含两个数组
      if (result.data.teaching_factory && result.data.factory_count) {
        updateFactoryChart(result.data);
      } else if (Array.isArray(result.data)) {
        // 兼容数组格式
        updateFactoryChart(result.data);
      } else {
        console.warn("厂区数据格式不正确:", result.data);
        // 清空图表数据
        factoryChartOption.value.xAxis.data = [];
        factoryChartOption.value.series[0].data = [];
      }
    } else {
      console.warn("获取厂区数据失败:", result.message);
      // 清空图表数据
      factoryChartOption.value.xAxis.data = [];
      factoryChartOption.value.series[0].data = [];
    }
  } catch (error) {
    console.error("获取厂区数据失败:", error);
    // 清空图表数据
    factoryChartOption.value.xAxis.data = [];
    factoryChartOption.value.series[0].data = [];
  }
};

// 获取教师分组数据
const fetchTeacherGroupData = async () => {
  if (!courseName.value) return;

  try {
    const response = await fetch(
      `api/teaching-record/group_coursename?course_name_value=${encodeURIComponent(
        courseName.value
      )}`
    );
    const result = await response.json();

    if (result.success && result.data) {
      updateRegionTableData(result.data);
    } else {
      console.warn("获取教师分组数据失败:", result.message);
      // 即使获取数据失败，也保持固定的表格结构
      updateRegionTableData([]);
    }
  } catch (error) {
    console.error("获取教师分组数据失败:", error);
    // 发生错误时，也保持固定的表格结构
    updateRegionTableData([]);
  }
};

// 更新教师分组表格数据
const updateRegionTableData = (apiData) => {
  // 按地区分组数据
  const groupedByDistrict = {};

  apiData.forEach((item) => {
    const district = item.district;
    const batchNumber = item.batch_number;

    if (!groupedByDistrict[district]) {
      groupedByDistrict[district] = {};
    }

    if (!groupedByDistrict[district][batchNumber]) {
      groupedByDistrict[district][batchNumber] = [];
    }

    // 判断是否合格规则：
    // 1) 平均分 avg_score 有效且 >= 94
    // 2) 同时，score_list 中不允许出现連續兩個(<94) 的分數，否則視為不合格
    const avg = Number(item.avg_score);
    const baseQualified = Number.isFinite(avg) && avg >= 94;

    // 解析 score_list，允許如 "95.00_list" 此類後綴文本，parseFloat 會自動截取數字部分
    const rawList = item.score_list;
    let scores = [];
    if (typeof rawList === "string" && rawList.trim() !== "") {
      scores = rawList
        .split(",")
        .map((s) => parseFloat(String(s).trim()))
        .filter((n) => Number.isFinite(n));
    }

    const hasTwoConsecutiveBelow = (arr, threshold = 94) => {
      let streak = 0;
      for (const n of arr) {
        if (Number.isFinite(n) && n < threshold) {
          streak += 1;
          if (streak >= 2) return true; // 發現連續兩個 < threshold
        } else {
          streak = 0; // 斷開連續
        }
      }
      return false;
    };

    const disqualify = hasTwoConsecutiveBelow(scores, 94);
    const qualified = baseQualified && !disqualify;

    groupedByDistrict[district][batchNumber].push({
      name: item.name,
      // 分數顯示保留兩位小數（僅用於右側表格展示，不影響圖表數據）
      score: Number.isFinite(avg) ? avg.toFixed(2) : item.avg_score,
      qualified: qualified,
      recordCount: item.record_count,
    });
  });

  // 固定的地区顺序，永远保持華南、華中、華北的排序
  const fixedRegionOrder = ["華南", "華中", "華北"];
  const newRegionTableData = [];

  // 按固定顺序创建地区表格数据
  fixedRegionOrder.forEach((regionName) => {
    const floors = [];
    const district = groupedByDistrict[regionName] || {}; // 如果地区没有数据，使用空对象

    // 创建4个批次 (1棒, 2棒, 3棒, 4棒)
    for (let i = 1; i <= 4; i++) {
      floors.push({
        floor: `${i}棒`,
        teachers: district[i] || [], // 如果该批次没有数据，则为空数组
      });
    }

    newRegionTableData.push({
      name: regionName,
      floors: floors,
    });
  });

  // 更新响应式数据
  regionTableData.value = newRegionTableData;
};

// 初始化
onMounted(async () => {
  await fetchCourseOptions();
  if (courseName.value) {
    await Promise.all([
      fetchTeachingRecords(),
      fetchFactoryData(),
      fetchTeacherGroupData(),
    ]);
  }
});

// 监听课程名称变化
watch(
  courseName,
  (newCourseName) => {
    if (newCourseName) {
      Promise.all([
        fetchTeachingRecords(),
        fetchFactoryData(),
        fetchTeacherGroupData(),
      ]);
    }
  },
  { immediate: false }
);

// 统计数据
const totalTrial = ref(0);
const totalTest = ref(0);
const totalDelivery = ref(0);
const totalAverage = ref(0);

// 存储图表详细数据，用于tooltip显示
const chartDetailsData = ref([]);

// 更新图表数据
const updateChartData = (data) => {
  // 保存详细数据供tooltip使用
  chartDetailsData.value = data;

  // 提取教学类型和平均分
  // const teachingTypes = data.map((item) => item.teaching_type);
  const teachingTypes = data.map((item) => item.new_teaching_type);
  const avgScores = data.map((item) => item.avg_score);

  // 计算分割线位置
  const separatorLines = calculateSeparatorLines(teachingTypes);

  // 生成阶段标签
  const stageLabels = generateStageLabels(teachingTypes);

  // 生成合格线数据
  const qualificationLines = generateQualificationLines(teachingTypes);

  // 生成左右兩端標註文本（左90，右94）
  const edgeLabelSeries = generateEdgeLabelSeries(teachingTypes);

  // 更新图表配置
  progressChartOption.value = {
    ...progressChartOption.value,
    xAxis: {
      ...progressChartOption.value.xAxis,
      data: teachingTypes,
    },
    series: [
      {
        name: "得分",
        type: "line",
        data: avgScores,
        itemStyle: {
          color: "#3875C5",
        },
        lineStyle: {
          color: "#3875C5",
          width: 3,
        },
        symbol: "circle",
        symbolSize: 8,
        label: {
          show: true,
          position: "top",
          color: "#000",
          fontSize: 12,
          // formatter: "{c}",
          formatter: (params) => {
            return params.data.toFixed(2);
          },
        },
        markLine: {
          silent: true,
          lineStyle: {
            color: "rgba(0, 0, 0, 0.6)",
            type: "dashed",
            width: 2,
          },
          data: separatorLines,
          label: {
            show: false,
          },
          symbol: "none", // 去掉箭头
        },
      },
      ...qualificationLines,
      ...(edgeLabelSeries ? edgeLabelSeries : []),
    ],
    // 添加阶段标签
    graphic: [
      ...stageLabels.map((label) => ({
        type: "text",
        left: `${((label.coord[0] + 0.5) / teachingTypes.length) * 100}%`,
        top: "5%",
        style: {
          text: label.value,
          fill: "rgba(0, 0, 0, 0.9)",
          fontSize: 16,
          fontWeight: "bold",
          textAlign: "center",
        },
      })),
    ],
  };
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
  if (lastTrialIndex !== -1 && firstTestIndex !== -1) {
    const separatorPosition = lastTrialIndex + 0.5;
    separators.push({
      xAxis: separatorPosition,
    });
  }

  // 在最后一个試跑和第一个正式交付之间添加分割线
  if (lastTestIndex !== -1 && firstDeliveryIndex !== -1) {
    const separatorPosition = lastTestIndex + 0.5;
    separators.push({
      xAxis: separatorPosition,
    });
  }

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
        color: "rgba(0, 0, 0, 0.9)",
      },
    });
  }

  if (testStart !== -1) {
    stages.push({
      coord: [(testStart + testEnd) / 2, 80],
      value: "試跑階段",
      itemStyle: {
        color: "rgba(0, 0, 0, 0.9)",
      },
    });
  }

  if (deliveryStart !== -1) {
    stages.push({
      coord: [(deliveryStart + deliveryEnd) / 2, 80],
      value: "正式交付階段",
      itemStyle: {
        color: "rgba(0, 0, 0, 0.9)",
      },
    });
  }

  return stages;
};

// 生成合格线数据
const generateQualificationLines = (teachingTypes) => {
  // 按教学类型分组：試點、試跑、正式交付
  let trialCount = 0;
  let testCount = 0;
  let deliveryCount = 0;

  teachingTypes.forEach((type) => {
    if (type.includes("試點")) {
      trialCount++;
    } else if (type.includes("試跑")) {
      testCount++;
    } else if (type.includes("正式交付")) {
      deliveryCount++;
    }
  });

  const total = teachingTypes.length;

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
    },
  ];
};

// 生成左右兩端標註文本（左90，右94），以散點系列形式加入，不影響 tooltip 與圖例
const generateEdgeLabelSeries = (teachingTypes) => {
  if (!Array.isArray(teachingTypes) || teachingTypes.length === 0) return null;
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
      color: "#C00000",
      offset: [-10, 0],
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

// 更新统计数据
const updateStatistics = (data) => {
  let trialCount = 0;
  let testCount = 0;
  let deliveryCount = 0;
  let averageCount = 0;

  data.forEach((item) => {
    if (item.teaching_type.includes("試點")) {
      trialCount++;
    } else if (item.teaching_type.includes("試跑")) {
      testCount++;
    } else if (item.teaching_type.includes("正式交付")) {
      deliveryCount++;
      averageCount = averageCount + item.avg_score;
    }
  });

  totalTrial.value = trialCount;
  totalTest.value = testCount;
  totalDelivery.value = deliveryCount;
  // 顯示“正式交付平均分”：僅針對正式交付求平均並保留兩位小數
  totalAverage.value = deliveryCount
    ? parseFloat((averageCount / deliveryCount).toFixed(2))
    : 0;
};

// 更新厂区图表数据
const updateFactoryChart = (data) => {
  try {
    let factories = [];
    let counts = [];

    // 判断数据格式
    if (data.teaching_factory && data.factory_count) {
      // 新格式：对象包含两个数组
      if (
        Array.isArray(data.teaching_factory) &&
        Array.isArray(data.factory_count)
      ) {
        factories = data.teaching_factory;
        // 使用纯数值，颜色由 series.itemStyle 的渐变统一控制
        counts = data.factory_count.map((count) => count || 0);
      } else {
        console.warn("厂区数据字段不是数组:", data);
        return;
      }
    } else if (Array.isArray(data)) {
      // 旧格式：数组格式（兼容性支持）
      if (data.length === 0) {
        console.warn("厂区数据为空");
        factoryChartOption.value.xAxis.data = [];
        factoryChartOption.value.series[0].data = [];
        return;
      }

      factories = data.map((item) => {
        if (!item || typeof item !== "object") {
          console.warn("无效的数据项:", item);
          return "";
        }
        return item.teaching_factory || "";
      });

      counts = data.map((item) => {
        if (!item || typeof item !== "object") {
          console.warn("无效的数据项:", item);
          return 0;
        }
        return item.factory_count || 0;
      });
    } else {
      console.warn("未知的厂区数据格式:", data);
      factoryChartOption.value.xAxis.data = [];
      factoryChartOption.value.series[0].data = [];
      return;
    }

    // console.log("处理后的厂区数据:", { factories, counts }); // 调试日志

    // 更新图表配置
    factoryChartOption.value = {
      ...factoryChartOption.value,
      xAxis: {
        ...factoryChartOption.value.xAxis,
        data: factories,
      },
      series: [
        {
          ...factoryChartOption.value.series[0],
          data: counts,
        },
      ],
    };
  } catch (error) {
    console.error("处理厂区图表数据时出错:", error);
    // 设置空数据作为后备
    factoryChartOption.value.xAxis.data = [];
    factoryChartOption.value.series[0].data = [];
  }
};

// 进度折线图配置 - 初始配置，数据将由API动态更新
const progressChartOption = ref({
  tooltip: {
    trigger: "axis",
    backgroundColor: "rgba(255,255,255,0.8)",
    borderColor: "rgba(0,0,0,0.2)",
    textStyle: {
      color: "#000",
    },
    formatter: function (params) {
      // 自定义tooltip内容，显示details数据
      if (!params || params.length === 0) return "";

      const dataIndex = params[0].dataIndex;
      const teachingType = params[0].name;

      // 获取对应的details数据
      const currentData = chartDetailsData.value[dataIndex];
      if (!currentData || !currentData.details) {
        return `${teachingType}<br/>暂无详细数据`;
      }

      let tooltipContent = `<div style="font-weight: bold; margin-bottom: 8px;">${teachingType}</div>`;
      const avgDisplay = Number.isFinite(Number(currentData.avg_score))
        ? Number(currentData.avg_score).toFixed(2)
        : currentData.avg_score;
      tooltipContent += `<div style="margin-bottom: 5px;">平均分: ${avgDisplay}</div>`;
      // tooltipContent += `<div style="margin-bottom: 8px;">记录数: ${currentData.record_count}</div>`;
      tooltipContent += `<div style="font-weight: bold; margin-bottom: 5px;">详细分数:</div>`;

      currentData.details.forEach((detail) => {
        const [name, score] = detail.split(":");
        const displayScore = Number.isFinite(Number(score))
          ? Number(score).toFixed(2)
          : score;
        tooltipContent += `<div style="margin-left: 10px; margin-bottom: 2px;">• ${name}: ${displayScore}</div>`;
      });

      return tooltipContent;
    },
  },
  legend: {
    data: ["得分", "合格線"],
    textStyle: {
      color: "#000",
      fontSize: 14,
    },
    right: "5%",
    top: "3%",
  },
  grid: {
    left: "2%",
    right: "3%",
    bottom: "5%",
    top: "15%",
    containLabel: true,
  },
  xAxis: {
    type: "category",
    data: [], // 将由API数据动态填充
    // axisLabel: {
    //   color: "#000",
    //   fontSize: 16,
    // },
    axisLabel: {
      // formatter: function (value) {
      //   // 使用正则表达式分割：保留连续数字和单个中文字符
      //   return value
      //     .replace(/(\d+)|(\D)/g, (matched, num, nonNum) => {
      //       return num ? `${num}` : `${nonNum}\n`; // 数字保留整体，非数字拆分并加换行
      //     })
      //     .trim();
      // },
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
      fontSize: 13,
      //   margin: 15, // 标签与轴线间距
      //   inside: false, // 标签显示在轴线外侧
    },

    axisLine: {
      lineStyle: {
        color: "rgba(0,0,0,0.3)",
      },
    },
  },
  yAxis: {
    type: "value",
    min: 80,
    max: 100,
    // show: false,
    axisLabel: {
      color: "#000",
      fontSize: 14,
    },
    axisLine: {
      lineStyle: {
        color: "rgba(0,0,0,0.3)",
      },
    },
    splitLine: {
      lineStyle: {
        color: "rgba(0,0,0,0.1)",
      },
    },
  },
  series: [], // 将由API数据动态填充
});

// 厂区统计柱状图配置 - 初始配置，数据将由API动态更新
const factoryChartOption = ref({
  title: {
    text: "BY廠區正式交付授課數量",
    textStyle: {
      color: "#000",
      fontSize: 16,
      fontWeight: "bold",
    },
    left: "center",
    top: "5%",
  },
  tooltip: {
    trigger: "axis",
    backgroundColor: "rgba(255,255,255,0.8)",
    borderColor: "rgba(0,0,0,0.2)",
    textStyle: {
      color: "#000",
    },
  },
  grid: {
    left: "5%",
    right: "5%",
    bottom: "15%",
    top: "25%",
    containLabel: true,
  },
  xAxis: {
    type: "category",
    data: [], // 将由API数据动态填充
    // axisLabel: {
    //   color: "#000",
    //   fontSize: 12,
    // },
    axisLabel: {
      formatter: function (value) {
        // 使用正则表达式分割：保留连续数字和单个中文字符
        return value
          .replace(/(\d+)|(\D)/g, (matched, num, nonNum) => {
            return num ? `${num}` : `${nonNum}\n`; // 数字保留整体，非数字拆分并加换行
          })
          .trim();
      },
      rotate: 0, // 标签逆时针旋转45度
      interval: 0, // 强制显示所有标签（避免自动隐藏）
      color: "#000",
      fontSize: 13,
      //   margin: 15, // 标签与轴线间距
      //   inside: false, // 标签显示在轴线外侧
    },
    axisLine: {
      lineStyle: {
        color: "rgba(0,0,0,0.3)",
      },
    },
  },
  yAxis: {
    type: "value",
    axisLabel: {
      color: "#000",
      fontSize: 15,
      show: false,
    },
    axisLine: {
      lineStyle: {
        color: "rgba(0,0,0,0.3)",
      },
    },
    splitLine: {
      lineStyle: {
        color: "rgba(0,0,0,0.1)",
      },
    },
  },
  series: [
    {
      type: "bar",
      data: [], // 将由API数据动态填充
      barWidth: 30,
      itemStyle: {
        // 使用线性渐变颜色（上亮下深）
        color: {
          type: "linear",
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: "#5a9db0" }, // 顶部高亮青色
            { offset: 1, color: "#98c2ce" }, // 底部深青色
          ],
          global: false,
        },
        borderRadius: [0, 0, 0, 0],
        shadowColor: "rgba(0,0,0,0.15)",
        shadowBlur: 6,
      },
      label: {
        show: true,
        position: "top",
        color: "#000",
        fontSize: 14,
        // fontWeight: "bold",
        formatter: "{c}",
      },
    },
  ],
});

// 地区教师数据 - 将由API动态更新
const regionTableData = ref([
  {
    name: "華南",
    floors: [
      { floor: "1棒", teachers: [] },
      { floor: "2棒", teachers: [] },
      { floor: "3棒", teachers: [] },
      { floor: "4棒", teachers: [] },
    ],
  },
  {
    name: "華中",
    floors: [
      { floor: "1棒", teachers: [] },
      { floor: "2棒", teachers: [] },
      { floor: "3棒", teachers: [] },
      { floor: "4棒", teachers: [] },
    ],
  },
  {
    name: "華北",
    floors: [
      { floor: "1棒", teachers: [] },
      { floor: "2棒", teachers: [] },
      { floor: "3棒", teachers: [] },
      { floor: "4棒", teachers: [] },
    ],
  },
]);

// 返回功能  返回到Dashboard页面
const goBack = () => {
  router.push({
    name: "Dashboard",
  });
};

// 刷新功能
const refreshPage = async () => {
  if (refreshing.value || loading.value) return;

  refreshing.value = true;
  try {
    // 重新加载数据
    await fetchCourseOptions();
    if (courseName.value) {
      await Promise.all([
        fetchTeachingRecords(),
        fetchFactoryData(),
        fetchTeacherGroupData(),
      ]);
    }
    ElMessage({
      message: "刷新成功",
      type: "success",
      duration: 1500,
    });
  } catch (error) {
    ElMessage({
      message: "刷新失败",
      type: "error",
      duration: 2000,
    });
  } finally {
    refreshing.value = false;
  }
};

// 导出功能
// 新的讲师/课程导出逻辑，按照提供的示例实现
const exportLecturer = async (name) => {
  try {
    const resp = await fetch(
      `api/teaching-record/line_coursename?course_name_value=${encodeURIComponent(
        name
      )}&export_csv=true`
    );

    // 尝试解析为 JSON（后端应返回包含文件信息的 JSON）
    const data = await resp.json().catch(async () => {
      // 如果不是 JSON（说明还是旧的直接返回文件流方式），则回退到 blob 下载
      const blob = await resp.blob();
      return { legacyBlob: blob };
    });

    // 新协议：data.success && data.file?.url
    if (data && data.success && data.file?.url) {
      const a = document.createElement("a");
      a.href = data.file.url;
      a.download = data.file.name || `${name}_${timestamp}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      return true;
    }

    // 兼容旧逻辑：直接是文件流（legacyBlob）
    if (data.legacyBlob instanceof Blob) {
      const url = window.URL.createObjectURL(data.legacyBlob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${name}_${timestamp}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      return true;
    }

    // 解析失败的情况
    console.warn("未检测到可用的文件信息", data);
    return false;
  } catch (e) {
    console.error("导出异常:", e);
    return false;
  }
};

const handleExport = async () => {
  if (!courseName.value) {
    ElMessage({
      message: "請先選擇課程",
      type: "warning",
      duration: 2000,
    });
    return;
  }

  ElMessage({
    message: `正在導出課程《${courseName.value}》的教學記錄...`,
    type: "info",
    duration: 1500,
  });

  const ok = await exportLecturer(courseName.value);
  if (ok) {
    ElMessage({
      message: "導出成功",
      type: "success",
      duration: 2000,
    });
  } else {
    ElMessage({
      message: "導出失败，請稍後重試",
      type: "error",
      duration: 3000,
    });
  }
};

// 跳转到讲师分析页面
const goToLecturerAnalysis = (teacher) => {
  if (!teacher || !teacher.name) {
    ElMessage({
      message: "教師信息不完整",
      type: "warning",
      duration: 2000,
    });
    return;
  }

  // 跳转到讲师分析页面，传递教师姓名作为参数
  router.push({
    name: "LecturerAnalysis",
    query: {
      lecturer: teacher.name,
      course: courseName.value,
    },
  });
};

// 获取地区中最大的教师行数，最少5行
const getMaxTeachersInFloor = (region) => {
  const maxTeachers = Math.max(
    ...region.floors.map((floor) => floor.teachers.length),
    1
  );
  // console.log(`地区 ${region.name} 最大教师数:`, maxTeachers); // 调试信息
  return Math.max(maxTeachers, 5);
};

// 获取教师单元格的样式类
const getTeacherCellClass = (teacher) => {
  if (!teacher) return "teacher-cell empty-cell";
  return teacher.qualified
    ? "teacher-cell qualified-cell"
    : "teacher-cell pending-cell";
};
</script>

<style scoped>
@import "@/style/general.css";
.top-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 30px;
  width: 100%;
}

.back-section {
  flex: 0 0 auto;
  display: flex;
  gap: 12px;
  align-items: center;
}

.custom-btn {
  background: linear-gradient(45deg, #3875c5, #3875c5);
  border: 1px solid rgba(255, 255, 255, 0.25);
  color: #fff;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  padding: 0 14px;
  height: 32px;
  min-width: 60px;
  display: flex;
  align-items: center;
  box-shadow: 0 1px 4px rgba(30, 58, 138, 0.06);
  transition: all 0.2s;
}
.custom-btn .el-icon {
  margin-right: 4px;
  font-size: 15px;
}
.btn-text {
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.5px;
}

.placeholder {
  flex: 0 0 auto;
  width: 120px; /* 与返回按钮宽度保持平衡 */
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

.course-title {
  color: black;
  font-size: 24px;
  font-weight: bold;
  margin: 0;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
  text-align: center;
  width: 100%;
}

.status-filter {
  position: absolute;
  right: 10px;
}

.status-select {
  width: 200px;
}

:deep(.el-select .el-input__wrapper) {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.3);
  backdrop-filter: blur(10px);
}

:deep(.el-select .el-input__inner) {
  color: white;
}

.content {
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: calc(100vh - 180px);
  height: auto;
  overflow: visible;
}

/* 上半部分：折线图 */
.top-section {
  height: 500px;
  min-height: 400px;
  flex-shrink: 0;
  animation: slideInLeft 0.8s ease-out;
}

.full-width {
  width: 100%;
  height: 100%;
  min-height: 0;
}

/* 下半部分：柱状图 + 教师数据 */
.bottom-section {
  flex: 0 0 auto;
  min-height: 450px; /* 增加高度确保所有内容显示 */
  height: 450px;
  display: flex;
  gap: 20px;
  animation: slideInRight 0.8s ease-out;
}

/* 左侧1/4：柱状图 */
.left-quarter {
  width: 30%;
  height: 100%;
  min-height: 0;
}

/* 右侧3/4：教师数据 */
.right-three-quarters {
  width: 70%;
  height: 100%;
  min-height: 0;
  background: rgba(255, 255, 255, 0.12);
  border-radius: 15px;
  padding: 15px 15px 20px 15px; /* 确保底部有足够空间 */
  backdrop-filter: blur(15px);
  border: 1px solid rgba(255, 255, 255, 0.25);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  overflow: visible; /* 改为visible以显示地区标签 */
  box-sizing: border-box;
  position: relative;
}

.chart-container {
  background: rgba(255, 255, 255, 0.12);
  border-radius: 15px;
  padding: 15px;
  backdrop-filter: blur(15px);
  border: 1px solid rgba(255, 255, 255, 0.25);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  height: 100%;
  max-height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

.chart-container:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
  border-color: rgba(255, 255, 255, 0.3);
}

.chart-wrapper {
  display: flex;
  flex-direction: column;
  height: 100%;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.progress-chart {
  flex: 1;
  width: 100%;
  min-height: 0;
  max-height: calc(100% - 100px);
}

.progress-stats {
  display: flex;
  justify-content: center;
  gap: 60px;
  padding: 10px 0;
  margin-top: 5px;
  flex-shrink: 0;
  height: 80px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
}

.stat-number {
  color: #e44904;
  font-size: 36px;
  font-weight: bold;
  line-height: 1;
  /* text-shadow: 0 0 20px rgba(255, 107, 107, 0.5); */
}

.stat-label {
  color: black;
  font-size: 16px;
  font-weight: 500;
}

.factory-stats {
  background: rgba(255, 255, 255, 0.12);
  border-radius: 15px;
  padding: 10px;
  backdrop-filter: blur(15px);
  border: 1px solid rgba(255, 255, 255, 0.25);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  height: 100%;
  transition: all 0.3s ease;
  overflow: hidden;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
}

.factory-stats:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
  border-color: rgba(255, 255, 255, 0.3);
}

.factory-chart {
  width: 100%;
  flex: 1;
  min-height: 0;
}

.table-header {
  color: black;
  font-size: 16px;
  margin-bottom: 8px;
  font-weight: bold;
  text-align: center;
  flex-shrink: 0;
}

.legend-bar {
  display: flex;
  justify-content: center;
  gap: 30px;
  margin-bottom: 10px;
  padding: 8px 0;
  flex-shrink: 0;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  color: black;
  font-size: 14px;
  font-weight: 500;
}

.legend-dot {
  width: 12px;
  height: 12px;
  border-radius: 2px;
}

.legend-item.completed .legend-dot {
  background-color: #5a9db0;
}

.legend-item.pending .legend-dot {
  background-color: #8064a2;
}

.teacher-tables-container {
  flex: 1;
  display: flex;
  justify-content: space-between;
  gap: 20px; /* 增加表格间距 */
  padding: 10px 0 45px 0; /* 增加底部空间给地区标签 */
  overflow: visible;
  min-height: 0;
  height: calc(100% - 90px);
  position: relative;
}

.region-table {
  flex: 1;
  background: rgba(255, 255, 255, 0.05);
  border: 3px solid rgba(255, 255, 255, 0.4); /* 增强外边框 */
  border-radius: 12px;
  overflow: visible; /* 改为visible确保内容显示 */
  position: relative;
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 280px; /* 设置最小高度确保5行都能显示 */
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2); /* 添加阴影增强分离感 */
}

.region-table:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
  border-color: rgba(255, 255, 255, 0.4);
}

.table-header-row {
  display: flex;
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.2),
    rgba(255, 255, 255, 0.1)
  );
  border-bottom: 2px solid rgba(255, 255, 255, 0.3);
}

.floor-header-cell {
  flex: 1;
  padding: 12px 8px;
  text-align: center;
  color: black;
  font-weight: bold;
  font-size: 14px;
  border-right: 2px solid rgba(255, 255, 255, 0.4); /* 增强头部垂直分割线 */
  background: rgba(255, 255, 255, 0.1);
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

.floor-header-cell:last-child {
  border-right: none;
}

.table-body {
  display: flex;
  flex-direction: column;
  flex: 1;
  height: 100%;
  min-height: 200px; /* 确保有足够高度显示5行 */
}

.table-row {
  display: flex;
  border-bottom: 2px solid rgba(255, 255, 255, 0.3); /* 增强水平分割线 */
  flex: 1;
  min-height: 35px; /* 增加行高确保内容可见 */
  height: auto;
}

.table-row:last-child {
  border-bottom: none;
}

.teacher-cell {
  flex: 1;
  padding: 8px;
  text-align: center;
  border-right: 2px solid rgba(255, 255, 255, 0.4); /* 增强垂直分割线 */
  border-bottom: 1px solid rgba(255, 255, 255, 0.3); /* 添加水平分割线 */
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  position: relative;
  border-radius: 4px;
  margin: 1px; /* 减小边距让分割线更明显 */
}

.teacher-cell:last-child {
  border-right: none; /* 最后一列不显示右边框 */
}

.qualified-cell {
  background: linear-gradient(135deg, #5a9db0, #5a9db0);
  color: white;
  /* border: 1px solid rgba(56, 117, 197, 0.8);
  box-shadow: 0 2px 4px rgba(56, 117, 197, 0.3); */
}

.pending-cell {
  background: linear-gradient(135deg, #8064a2, #8064a2);
  color: white;
  /* border: 1px solid rgba(255, 107, 107, 0.8); */
  /* box-shadow: 0 2px 4px rgba(255, 107, 107, 0.3); */
}

.empty-cell {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.teacher-cell:hover:not(.empty-cell) {
  transform: scale(1.05);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4);
  z-index: 10;
}

.teacher-info {
  color: white;
  font-weight: 600;
  text-align: center;
  line-height: 1.2;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
  cursor: pointer;
  transition: all 0.3s ease;
  border-radius: 4px;
  padding: 2px;
}

.teacher-info:hover {
  background: rgba(255, 255, 255, 0.1);
  transform: scale(1.05);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.teacher-name {
  font-size: 12px;
  margin-bottom: 2px;
  font-weight: bold;
}

.teacher-score {
  font-size: 10px;
  opacity: 0.9;
}

.region-label {
  position: absolute;
  bottom: -32px; /* 调整位置确保可见 */
  left: 50%;
  transform: translateX(-50%);
  color: #333;
  font-weight: 700;
  font-size: 16px; /* 纯文字显示 */
  text-shadow: none;
  background: transparent; /* 去掉背景格子 */
  padding: 0; /* 去掉内边距 */
  border-radius: 0; /* 去掉圆角 */
  border: none; /* 去掉边框 */
  backdrop-filter: none; /* 去掉毛玻璃效果 */
  z-index: 20; /* 保持在上层便于可见 */
  white-space: nowrap;
  box-shadow: none; /* 去掉阴影 */
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

/* 响应式设计 */
@media (max-width: 1200px) {
  .content {
    height: auto;
    min-height: calc(100vh - 120px);
  }

  .top-section {
    height: 400px;
    min-height: 400px;
  }

  .bottom-section {
    flex-direction: column;
    min-height: 600px;
  }

  .left-quarter {
    width: 100%;
    height: 350px;
  }

  .right-three-quarters {
    width: 100%;
    height: 500px;
  }
}

@media (max-width: 768px) {
  .dashboard-container {
    padding: 10px;
  }

  .course-title {
    font-size: 20px;
  }

  .teacher-tables-container {
    flex-direction: column;
    gap: 20px;
  }

  .region-table {
    margin-bottom: 50px; /* 为地区标签留更多空间 */
  }

  .floor-header-cell {
    padding: 10px 6px;
    font-size: 12px;
  }

  .teacher-cell {
    padding: 6px 4px;
  }

  .teacher-name {
    font-size: 11px;
  }

  .teacher-score {
    font-size: 9px;
  }

  .region-label {
    font-size: 14px;
    bottom: -30px;
  }

  .progress-stats {
    gap: 30px;
  }

  .stat-number {
    font-size: 36px;
  }

  .top-section {
    height: 350px;
    min-height: 350px;
  }

  .bottom-section {
    flex-direction: column;
    min-height: 500px;
  }

  .left-quarter {
    width: 100%;
    height: 300px;
  }

  .right-three-quarters {
    width: 100%;
    height: 450px;
  }
}
</style>
