<template>
  <div class="dashboard-container">
    <div class="header">
      <h1>翰林院-品保（8分钟）</h1>
    </div>
    <!-- 顶部导航栏 -->
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

      <div class="placeholder"></div>
    </div>

    <!-- 申请人填筛区域 -->
    <div class="form-section">
      <div class="section-header">
        <el-icon class="section-icon"><User /></el-icon>
        <span class="section-title">申請人填写：</span>
      </div>

      <div class="form-container">
        <el-form
          :model="applicationForm"
          label-width="100px"
          class="application-form"
        >
          <div class="form-row">
            <el-form-item label="申請日期" class="form-field">
              <el-date-picker
                v-model="applicationForm.applicationDate"
                type="datetime"
                placeholder="請選擇申請日期時間"
                format="YYYY-MM-DD HH:mm:ss"
                value-format="YYYY-MM-DD HH:mm:ss"
                style="width: 90%"
                :default-time="new Date()"
                :editable="false"
                :clearable="true"
              />
            </el-form-item>
            <el-form-item label="申請人" class="form-field">
              <el-input
                v-model="applicationForm.applicant"
                placeholder="請輸入申請人"
              />
            </el-form-item>
            <el-form-item label="工號" class="form-field">
              <el-input
                v-model="applicationForm.employeeId"
                placeholder="請輸入工號"
              />
            </el-form-item>
            <el-form-item label="部門" class="form-field">
              <el-input
                v-model="applicationForm.department"
                placeholder="請輸入部門"
              />
            </el-form-item>
            <el-form-item label="試講課程" class="form-field">
              <el-input
                v-model="applicationForm.course"
                placeholder="請輸入試講課程"
              />
            </el-form-item>
            <el-form-item label="戰區" class="form-field">
              <el-select
                v-model="applicationForm.area"
                placeholder="請選擇戰區"
              >
                <el-option label="華南" value="華南" />
                <el-option label="華北" value="華北" />
                <el-option label="華中" value="華中" />
              </el-select>
            </el-form-item>
            <el-form-item label="棒次" class="form-field">
              <el-input
                v-model="applicationForm.shift"
                placeholder="請輸入棒次"
              />
            </el-form-item>
          </div>

          <div class="submit-section">
            <el-button
              class="submit-btn"
              type="success"
              @click="submitApplication"
              :loading="submitting"
              :disabled="submitting"
            >
              {{ submitting ? "提交中..." : "申請" }}
            </el-button>
          </div>
        </el-form>
      </div>
    </div>

    <!-- 近1個月試講明細 -->
    <div class="detail-section">
      <div class="section-header">
        <el-icon class="section-icon"><List /></el-icon>
        <span class="section-title">近1個月試講明細：</span>
        <div class="header-actions">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索申请人、部门、課程、戰區或棒次"
            clearable
            class="search-input"
            style="width: 210px; margin-right: 10px"
            @keyup.enter="searchLectureData(searchKeyword)"
            @clear="searchLectureData('')"
            @input="handleSearchInput"
          >
          </el-input>

          <el-button
            class="export-btn"
            type="primary"
            @click="exportData"
            :loading="exporting"
            :disabled="exporting"
          >
            {{ exporting ? "導出中..." : "導出" }}
          </el-button>
        </div>
      </div>

      <div class="table-container">
        <el-table
          :data="lectureData"
          :header-cell-style="{ backgroundColor: '#1e3a8a', color: '#fff' }"
          class="lecture-table"
          stripe
          style="width: 100%"
          v-loading="loading"
          element-loading-text="正在加载数据..."
          element-loading-background="rgba(0, 0, 0, 0.3)"
          :height="400"
        >
          <el-table-column
            prop="applicationDate"
            label="申請日期"
            :width="columnWidths.applicationDate"
            align="center"
          >
            <template #header>
              <div class="th-content">
                申請日期
                <span
                  class="col-resizer"
                  @mousedown="(e) => startResize('applicationDate', e)"
                ></span>
              </div>
            </template>
          </el-table-column>
          <el-table-column
            prop="employeeId"
            label="工號"
            :width="columnWidths.employeeId"
            align="center"
          >
            <template #header>
              <div class="th-content">
                工號
                <span
                  class="col-resizer"
                  @mousedown="(e) => startResize('employeeId', e)"
                ></span>
              </div>
            </template>
          </el-table-column>
          <el-table-column
            prop="applicant"
            label="申請人"
            :width="columnWidths.applicant"
            align="center"
          >
            <template #header>
              <div class="th-content">
                申請人
                <span
                  class="col-resizer"
                  @mousedown="(e) => startResize('applicant', e)"
                ></span>
              </div>
            </template>
          </el-table-column>
          <el-table-column
            prop="department"
            label="部門"
            :width="columnWidths.department"
            align="center"
          >
            <template #header>
              <div class="th-content">
                部門
                <span
                  class="col-resizer"
                  @mousedown="(e) => startResize('department', e)"
                ></span>
              </div>
            </template>
          </el-table-column>
          <el-table-column
            prop="course"
            label="試講課程"
            :width="columnWidths.course"
            align="center"
            show-overflow-tooltip
          >
            <template #header>
              <div class="th-content">
                試講課程
                <span
                  class="col-resizer"
                  @mousedown="(e) => startResize('course', e)"
                ></span>
              </div>
            </template>
          </el-table-column>
          <el-table-column
            prop="area"
            label="戰區"
            :width="columnWidths.area"
            align="center"
          >
            <template #header>
              <div class="th-content">
                戰區
                <span
                  class="col-resizer"
                  @mousedown="(e) => startResize('area', e)"
                ></span>
              </div>
            </template>
          </el-table-column>
          <el-table-column
            prop="shift"
            label="棒次"
            :width="columnWidths.shift"
            align="center"
          >
            <template #header>
              <div class="th-content">
                棒次
                <span
                  class="col-resizer"
                  @mousedown="(e) => startResize('shift', e)"
                ></span>
              </div>
            </template>
          </el-table-column>
          <el-table-column
            prop="lectureDate"
            label="試講日期"
            :width="columnWidths.lectureDate"
            align="center"
          >
            <template #header>
              <div class="th-content">
                試講日期
                <span
                  class="col-resizer"
                  @mousedown="(e) => startResize('lectureDate', e)"
                ></span>
              </div>
            </template>
          </el-table-column>
          <el-table-column
            prop="score"
            label="試講得分"
            :width="columnWidths.score"
            align="center"
          >
            <template #header>
              <div class="th-content">
                試講得分
                <span
                  class="col-resizer"
                  @mousedown="(e) => startResize('score', e)"
                ></span>
              </div>
            </template>
          </el-table-column>
          <el-table-column
            prop="result"
            label="試講結果"
            :width="columnWidths.result"
            align="center"
          >
            <template #header>
              <div class="th-content">
                試講結果
                <span
                  class="col-resizer"
                  @mousedown="(e) => startResize('result', e)"
                ></span>
              </div>
            </template>
            <template #default="scope">
              <el-tag
                :type="
                  scope.row.result === '儲備講師'
                    ? 'success'
                    : scope.row.result === '未通過'
                    ? 'danger'
                    : 'danger'
                "
                size="small"
              >
                {{ scope.row.result || "未通過" }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            label="操作"
            :width="columnWidths.actions"
            align="center"
            fixed="right"
          >
            <template #header>
              <div class="th-content">
                操作
                <span
                  class="col-resizer"
                  @mousedown="(e) => startResize('actions', e)"
                ></span>
              </div>
            </template>
            <template #default="scope">
              <el-button
                type="primary"
                size="small"
                @click="editRecord(scope.row)"
                :disabled="loading"
              >
                编辑
              </el-button>
              <el-button
                type="danger"
                size="small"
                @click="confirmDelete(scope.row)"
                :disabled="loading"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页组件 -->
        <div class="pagination-container">
          <el-pagination
            v-model:current-page="pagination.current"
            v-model:page-size="pagination.pageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="pagination.total"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handlePageSizeChange"
            @current-change="handlePageChange"
            :disabled="loading"
          />
        </div>
      </div>
    </div>

    <!-- 编辑记录对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑試講记录"
      width="600px"
      :before-close="handleEditDialogClose"
    >
      <el-form
        :model="editForm"
        label-width="100px"
        class="edit-form"
        v-loading="editLoading"
      >
        <el-form-item label="申請日期">
          <el-date-picker
            v-model="editForm.applicationDate"
            type="datetime"
            placeholder="請選擇申請日期時間"
            format="YYYY-MM-DD HH:mm:ss"
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width: 100%"
            :editable="false"
            :clearable="false"
            :disabled="true"
          />
        </el-form-item>
        <el-form-item label="工號">
          <el-input
            v-model="editForm.employeeId"
            placeholder="請輸入工號"
            :disabled="true"
          />
        </el-form-item>
        <el-form-item label="申請人">
          <el-input
            v-model="editForm.applicant"
            placeholder="請輸入申請人"
            :disabled="true"
          />
        </el-form-item>
        <el-form-item label="部門">
          <el-input
            v-model="editForm.department"
            placeholder="請輸入部門"
            :disabled="true"
          />
        </el-form-item>
        <el-form-item label="試講課程">
          <el-input
            v-model="editForm.course"
            placeholder="請輸入試講課程"
            :disabled="true"
          />
        </el-form-item>
        <el-form-item label="戰區">
          <el-input
            v-model="editForm.area"
            placeholder="請輸入戰區"
            :disabled="true"
          />
        </el-form-item>
        <el-form-item label="棒次">
          <el-input
            v-model="editForm.shift"
            placeholder="請輸入棒次"
            :disabled="true"
          />
        </el-form-item>
        <el-form-item label="試講日期">
          <el-date-picker
            v-model="editForm.lectureDate"
            type="datetime"
            placeholder="請選擇試講日期時間"
            format="YYYY-MM-DD HH:mm:ss"
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width: 100%"
            :editable="false"
            :clearable="true"
          />
        </el-form-item>
        <el-form-item label="試講得分">
          <el-input-number
            v-model="editForm.score"
            :min="0"
            :max="100"
            placeholder="請輸入試講得分"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="試講結果">
          <el-select
            v-model="editForm.result"
            placeholder="請選擇試講結果"
            style="width: 100%"
          >
            <el-option label="未通過" value="未通過" />
            <el-option label="儲備講師" value="儲備講師" />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="handleEditDialogClose">取消</el-button>
          <el-button
            type="primary"
            @click="updateRecord"
            :loading="editSubmitting"
            :disabled="editSubmitting"
          >
            {{ editSubmitting ? "更新中..." : "更新" }}
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onUnmounted, onMounted } from "vue";
import { useRouter } from "vue-router";
import { User, ArrowLeft, Refresh, List } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";

const router = useRouter();

// 申请表单数据
const applicationForm = ref({
  applicationDate: "",
  applicant: "",
  employeeId: "",
  department: "",
  course: "",
  area: "",
  shift: "",
});

// 试讲明细数据 (根据图片内容调整)
const lectureData = ref([]);
const loading = ref(false);
const refreshing = ref(false);
const submitting = ref(false);
const exporting = ref(false);
// 列宽（可拖拽 + 持久化）
const columnWidths = ref({
  applicationDate: 240,
  applicant: 120,
  employeeId: 120,
  area: 120,
  department: 200,
  course: 250,
  shift: 100,
  lectureDate: 240,
  score: 100,
  result: 140,
  actions: 140,
});
const RESIZE_MIN = 60;
const RESIZE_MAX = 800;
const resizingState = ref(null);
// 取消列宽持久化：不再读写本地存储
const onMouseMove = (e) => {
  if (!resizingState.value) return;
  const { key, startX, startWidth } = resizingState.value;
  const delta = e.clientX - startX;
  let next = Math.max(RESIZE_MIN, Math.min(RESIZE_MAX, startWidth + delta));
  columnWidths.value[key] = Math.round(next);
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
onMounted(() => {});

// 分页相关数据
const pagination = ref({
  current: 1,
  pageSize: 10,
  total: 0,
  totalPages: 0,
});

// 搜索关键词
const searchKeyword = ref("");

// 编辑表单相关
const editDialogVisible = ref(false);
const editLoading = ref(false);
const editSubmitting = ref(false);
const currentEditId = ref(null);

// 编辑表单数据
const editForm = ref({
  applicationDate: "",
  applicant: "",
  employeeId: "",
  department: "",
  course: "",
  area: "",
  shift: "",
  lectureDate: "",
  score: null,
  result: "",
});

// 防抖时间控制
let refreshTimer = null;
let submitTimer = null;
let exportTimer = null;

// 获取试讲数据的函数 - 支持分页和搜索
const fetchLectureData = async (page = 1, limit = 10, search = "") => {
  loading.value = true;

  try {
    // 构建查询参数
    const params = new URLSearchParams({
      page: page.toString(),
      limit: limit.toString(),
      ...(search && { search }),
    });

    // 使用代理路径调用API接口获取数据
    const response = await fetch(`/api/Lecture?${params}`);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result = await response.json();

    if (result.success && result.data) {
      // 格式化日期字段
      const formatDate = (dateStr) => {
        if (!dateStr) return "";
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return dateStr;
        const pad = (n) => n.toString().padStart(2, "0");
        return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(
          d.getDate()
        )} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
      };

      lectureData.value = result.data.map((item) => ({
        ...item,
        applicationDate: formatDate(
          item.applicationDate || item.application_date || item.date
        ),
        lectureDate: formatDate(item.lectureDate || item.lecture_date),
      }));

      // 更新分页信息
      if (result.pagination) {
        pagination.value = result.pagination;
      }

      // console.log("API数据获取成功:", lectureData.value.length, "条记录");
      // ElMessage.success(`获取到 ${lectureData.value.length} 条记录`);
    } else {
      console.error("API返回数据格式错误:", result);
      ElMessage.error("数据获取失败");
    }
  } catch (error) {
    console.error("获取数据失败:", error);
    ElMessage.error("网络请求失败，请检查连接");

    // 发生错误时使用空数组
    lectureData.value = [];
  } finally {
    loading.value = false;
  }
};

// 初始化加载数据
fetchLectureData(pagination.value.current, pagination.value.pageSize);

// 提交申请 - 带防抖和状态控制 (POST API)
const submitApplication = () => {
  // 如果正在提交中，则忽略后续点击
  if (submitting.value) {
    ElMessage.warning("请等待提交完成");
    return;
  }

  // 表单验证
  const form = applicationForm.value;
  if (
    !form.applicationDate ||
    !form.applicant ||
    !form.employeeId ||
    !form.department ||
    !form.course ||
    !form.area ||
    !form.shift
  ) {
    ElMessage.error("请填写完整的申请信息");
    return;
  }

  // 清除之前的定时器
  if (submitTimer) {
    clearTimeout(submitTimer);
  }

  // 防抖：300ms 内的重复点击将被忽略
  submitTimer = setTimeout(async () => {
    try {
      submitting.value = true;
      ElMessage.info("正在提交申請...");

      // 调用创建API
      const response = await fetch("/api/Lecture", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          applicationDate: form.applicationDate,
          applicant: form.applicant,
          employeeId: form.employeeId,
          department: form.department,
          course: form.course,
          area: form.area,
          shift: form.shift,
        }),
      });

      const result = await response.json();

      if (result.success) {
        ElMessage.success("申請提交成功");

        // 提交成功后清空表单
        applicationForm.value = {
          applicationDate: "",
          applicant: "",
          employeeId: "",
          department: "",
          course: "",
          area: "",
          shift: "",
        };

        // 刷新列表数据
        await fetchLectureData(
          pagination.value.current,
          pagination.value.pageSize,
          searchKeyword.value
        );
      } else {
        ElMessage.error(result.message || "提交失败");
        console.error("创建失败:", result);
      }
    } catch (error) {
      console.error("提交失败:", error);
      ElMessage.error("提交失败，请重试");
    } finally {
      submitting.value = false;
    }
  }, 300);
};

// 更新培训记录 (PUT API) - 优化版本
const updateLectureRecord = async (id, updateData) => {
  try {
    // 1. 参数验证
    if (!id || typeof id !== "number") {
      const error = { success: false, message: "无效的记录ID" };
      ElMessage.error(error.message);
      return error;
    }

    // 2. 更新数据验证
    if (!updateData || Object.keys(updateData).length === 0) {
      const error = { success: false, message: "没有提供要更新的字段" };
      ElMessage.error(error.message);
      return error;
    }

    // 3. 数据类型和格式验证
    const validationResult = validateUpdateData(updateData);
    if (!validationResult.valid) {
      const error = { success: false, message: validationResult.message };
      ElMessage.error(error.message);
      return error;
    }

    // 4. 发送 PUT 请求
    const response = await fetch(`/api/Lecture/${id}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(updateData),
    });

    // 5. 处理 HTTP 状态码
    if (!response.ok) {
      let errorMessage = "更新失败";

      switch (response.status) {
        case 400:
          errorMessage = "请求参数错误或数据验证失败";
          break;
        case 404:
          errorMessage = "未找到指定的培训记录";
          break;
        case 409:
          errorMessage = "数据冲突，可能员工ID重复";
          break;
        case 500:
          errorMessage = "服务器内部错误，请稍后重试";
          break;
        default:
          errorMessage = `更新失败 (HTTP ${response.status})`;
      }

      ElMessage.error(errorMessage);
      return { success: false, message: errorMessage, status: response.status };
    }

    // 6. 解析响应数据
    const result = await response.json();

    if (result.success) {
      ElMessage.success("记录更新成功");

      // 7. 刷新列表数据
      await fetchLectureData(
        pagination.value.current,
        pagination.value.pageSize,
        searchKeyword.value
      );

      return { success: true, data: result.data };
    } else {
      ElMessage.error(result.message || "更新失败");
      return { success: false, message: result.message };
    }
  } catch (error) {
    console.error("更新失败:", error);

    // 8. 网络错误处理
    let errorMessage = "更新失败，请重试";
    if (error.name === "TypeError" && error.message.includes("fetch")) {
      errorMessage = "网络连接失败，请检查网络连接";
    } else if (error.name === "SyntaxError") {
      errorMessage = "服务器响应格式错误";
    }

    ElMessage.error(errorMessage);
    return { success: false, message: errorMessage, error: error.message };
  }
};

// 更新数据验证函数
const validateUpdateData = (updateData) => {
  const errors = [];

  // 验证结果状态
  if (updateData.hasOwnProperty("result")) {
    const validResults = ["未通過", "儲備講師", null];
    if (!validResults.includes(updateData.result)) {
      errors.push("无效的结果状态，只能是：未通過、儲備講師");
    }
  }

  // 验证日期格式 - 支持完整的 datetime 格式
  if (
    updateData.hasOwnProperty("applicationDate") &&
    updateData.applicationDate
  ) {
    // 支持多种日期格式：YYYY-MM-DD 或 YYYY-MM-DD HH:mm:ss
    const dateTimeRegex = /^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$/;
    if (!dateTimeRegex.test(updateData.applicationDate)) {
      errors.push("申请日期格式错误，应为 YYYY-MM-DD 或 YYYY-MM-DD HH:mm:ss");
    } else {
      const date = new Date(updateData.applicationDate);
      if (isNaN(date.getTime())) {
        errors.push("申请日期无效");
      }
    }
  }

  if (updateData.hasOwnProperty("lectureDate") && updateData.lectureDate) {
    // 支持多种日期格式：YYYY-MM-DD 或 YYYY-MM-DD HH:mm:ss
    const dateTimeRegex = /^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$/;
    if (!dateTimeRegex.test(updateData.lectureDate)) {
      errors.push("培训日期格式错误，应为 YYYY-MM-DD 或 YYYY-MM-DD HH:mm:ss");
    } else {
      const date = new Date(updateData.lectureDate);
      if (isNaN(date.getTime())) {
        errors.push("培训日期无效");
      }
    }
  }

  // 验证字符串长度
  const stringFields = {
    applicant: { max: 50, name: "申请人姓名" },
    employeeId: { max: 10, name: "员工编号" },
    department: { max: 100, name: "部门名称" },
    course: { max: 100, name: "课程名称" },
    area: { max: 50, name: "戰區" },
    shift: { max: 50, name: "棒次" },
  };

  Object.entries(stringFields).forEach(([field, config]) => {
    if (updateData.hasOwnProperty(field) && updateData[field]) {
      const value = String(updateData[field]).trim();
      if (value.length === 0) {
        errors.push(`${config.name}不能为空`);
      } else if (value.length > config.max) {
        errors.push(`${config.name}长度不能超过${config.max}个字符`);
      }
    }
  });

  return {
    valid: errors.length === 0,
    message: errors.length > 0 ? errors.join("；") : null,
    errors,
  };
};

// 删除培训记录 (DELETE API)
const deleteLectureRecord = async (id) => {
  try {
    const response = await fetch(`/api/Lecture/${id}`, {
      method: "DELETE",
    });

    const result = await response.json();

    if (result.success) {
      // ElMessage.success("记录删除成功");

      // 刷新列表数据
      await fetchLectureData(
        pagination.value.current,
        pagination.value.pageSize,
        searchKeyword.value
      );
      return { success: true };
    } else {
      ElMessage.error(result.message || "删除失败");
      return { success: false, message: result.message };
    }
  } catch (error) {
    console.error("删除失败:", error);
    ElMessage.error("删除失败，请重试");
    return { success: false, message: "网络错误" };
  }
};

// 获取单个记录详情 (GET API)
const getLectureRecordById = async (id) => {
  try {
    const response = await fetch(`/api/Lecture/${id}`);
    const result = await response.json();

    if (result.success) {
      console.log("获取记录详情成功:", result.data);
      return { success: true, data: result.data };
    } else {
      ElMessage.error(result.message || "获取记录失败");
      return { success: false, message: result.message };
    }
  } catch (error) {
    console.error("获取记录详情失败:", error);
    ElMessage.error("获取记录详情失败");
    return { success: false, message: "网络错误" };
  }
};

// 搜索培训记录
const searchLectureData = async (keyword) => {
  searchKeyword.value = keyword;
  pagination.value.current = 1; // 重置到第一页
  await fetchLectureData(1, pagination.value.pageSize, keyword);
};

// 搜索输入实时处理（防抖）
let searchTimer = null;
const handleSearchInput = (value) => {
  // 清除之前的定时器
  if (searchTimer) {
    clearTimeout(searchTimer);
  }

  // 如果输入为空，立即搜索
  if (!value.trim()) {
    searchLectureData("");
    return;
  }

  // 防抖：500ms 后执行搜索
  searchTimer = setTimeout(() => {
    searchLectureData(value);
  }, 500);
};

// 分页处理
const handlePageChange = async (page) => {
  pagination.value.current = page;
  await fetchLectureData(page, pagination.value.pageSize, searchKeyword.value);
};

// 页大小改变处理
const handlePageSizeChange = async (pageSize) => {
  pagination.value.pageSize = pageSize;
  pagination.value.current = 1; // 重置到第一页
  await fetchLectureData(1, pageSize, searchKeyword.value);
};

// 导出数据 - 带防抖和状态控制
const exportData = () => {
  // 如果正在导出中，则忽略后续点击
  if (exporting.value) {
    ElMessage.warning("请等待导出完成");
    return;
  }

  // 清除之前的定时器
  if (exportTimer) {
    clearTimeout(exportTimer);
  }

  // 防抖：300ms 内的重复点击将被忽略
  exportTimer = setTimeout(async () => {
    try {
      exporting.value = true;
      ElMessage.info("正在準備導出數據...");

      // 获取所有数据用于导出
      const response = await fetch("/api/Lecture?all=true");
      const result = await response.json();

      if (result.success && result.data) {
        // 日期格式化函数
        const formatDateTime = (dateStr) => {
          if (!dateStr) return "";
          const date = new Date(dateStr);
          if (isNaN(date.getTime())) return dateStr;

          const pad = (n) => n.toString().padStart(2, "0");
          return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(
            date.getDate()
          )} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(
            date.getSeconds()
          )}`;
        };

        // 格式化导出数据
        const exportData = result.data.map((item, index) => ({
          序号: index + 1,
          申请日期: formatDateTime(item.applicationDate),
          工号: item.employeeId,
          申请人: item.applicant,
          部门: item.department,
          戰區: item.area,
          棒次: item.shift,
          试讲课程: item.course,
          试讲日期: item.lectureDate
            ? formatDateTime(item.lectureDate)
            : "待安排",
          试讲得分: item.score || "未评分",
          试讲结果: item.result || "待安排",
        }));

        // 生成CSV格式数据
        const csvContent = [
          // CSV 头部
          Object.keys(exportData[0]).join(","),
          // CSV 数据行
          ...exportData.map((row) =>
            Object.values(row)
              .map(
                (value) => `"${String(value).replace(/"/g, '""')}"` // 处理CSV中的引号转义
              )
              .join(",")
          ),
        ].join("\n");

        // 创建下载链接
        const blob = new Blob(["\uFEFF" + csvContent], {
          type: "text/csv;charset=utf-8;",
        });
        const link = document.createElement("a");
        const url = URL.createObjectURL(blob);
        link.href = url;

        // 生成文件名时间戳格式：YYYYMMDDHHMMSS
        const now = new Date();
        const pad = (n) => n.toString().padStart(2, "0");
        const timestamp = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(
          now.getDate()
        )}${pad(now.getHours())}${pad(now.getMinutes())}${pad(
          now.getSeconds()
        )}`;

        link.download = `試講明細记录_${timestamp}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);

        ElMessage.success(`導出完成！共導出 ${exportData.length} 條記錄`);
        console.log("导出数据:", exportData);
      } else {
        ElMessage.warning("暂无数据可导出");
      }
    } catch (error) {
      console.error("导出失败:", error);
      ElMessage.error("導出失败，请重试");
    } finally {
      exporting.value = false;
    }
  }, 300);
};

// 刷新页面 - 带防抖和状态控制
const refreshPage = async () => {
  // 如果正在刷新中，则忽略后续点击
  if (refreshing.value || loading.value) {
    ElMessage.warning("请等待当前操作完成");
    return;
  }

  // 清除之前的定时器
  if (refreshTimer) {
    clearTimeout(refreshTimer);
  }

  // 防抖：500ms 内的重复点击将被忽略
  refreshTimer = setTimeout(async () => {
    try {
      refreshing.value = true;
      ElMessage.info("正在刷新数据...");

      // 重新获取试讲明细数据，保持当前分页和搜索状态
      await fetchLectureData(
        pagination.value.current,
        pagination.value.pageSize,
        searchKeyword.value
      );

      // 可选：重置申请表单
      applicationForm.value = {
        applicationDate: "",
        applicant: "",
        employeeId: "",
        department: "",
        course: "",
        area: "",
        shift: "",
      };

      // 重置搜索关键词
      searchKeyword.value = "";

      ElMessage.success("数据刷新完成");
    } catch (error) {
      console.error("刷新失败:", error);
      ElMessage.error("刷新失败，请重试");
    } finally {
      refreshing.value = false;
    }
  }, 500);
};

// 编辑记录处理
const editRecord = async (record) => {
  try {
    editLoading.value = true;
    editDialogVisible.value = true;
    currentEditId.value = record.id;

    ElMessage.info("正在加载记录详情...");

    // 获取记录详情
    const result = await getLectureRecordById(record.id);
    if (result.success) {
      // 填充编辑表单 - 确保日期时间格式正确
      const formatDateTimeForPicker = (dateStr) => {
        if (!dateStr) return "";

        // 如果是完整的 ISO 格式，直接使用
        if (dateStr.includes("T")) {
          return dateStr.replace("T", " ").split(".")[0]; // 转换为 YYYY-MM-DD HH:mm:ss 格式
        }

        // 如果已经是 YYYY-MM-DD HH:mm:ss 格式，直接返回
        if (dateStr.match(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/)) {
          return dateStr;
        }

        // 如果只是日期格式，添加时间
        if (dateStr.match(/^\d{4}-\d{2}-\d{2}$/)) {
          return dateStr + " 00:00:00";
        }

        return dateStr;
      };

      editForm.value = {
        applicationDate: formatDateTimeForPicker(
          result.data.applicationDate || ""
        ),
        applicant: result.data.applicant || "",
        employeeId: result.data.employeeId || "",
        department: result.data.department || "",
        course: result.data.course || "",
        area: result.data.area || "",
        shift: result.data.shift || "",
        lectureDate: formatDateTimeForPicker(result.data.lectureDate || ""),
        score: result.data.score || null,
        result: result.data.result || "未通過",
      };

      ElMessage.success("记录详情加载成功");
    } else {
      ElMessage.error("加载记录详情失败");
      editDialogVisible.value = false;
    }
  } catch (error) {
    console.error("编辑记录失败:", error);
    ElMessage.error("加载记录失败");
    editDialogVisible.value = false;
  } finally {
    editLoading.value = false;
  }
};

// 更新记录 - 优化版本，只允许修改试讲相关字段
const updateRecord = async () => {
  if (editSubmitting.value) {
    ElMessage.warning("请等待更新完成");
    return;
  }

  // 基础表单验证 - 检查必填字段是否存在（虽然不可编辑，但需要确保数据完整性）
  const form = editForm.value;
  if (
    !form.applicationDate ||
    !form.applicant ||
    !form.employeeId ||
    !form.department ||
    !form.course ||
    !form.area ||
    !form.shift
  ) {
    ElMessage.error("记录信息不完整，无法更新");
    return;
  }

  try {
    editSubmitting.value = true;
    ElMessage.info("正在更新记录...");

    // 构建更新数据对象 - 只包含可编辑的字段
    const updateData = {};

    // 只更新可编辑的字段：试讲日期、得分、结果
    if (form.lectureDate) {
      // 保持完整的日期时间格式
      updateData.lectureDate = form.lectureDate;
    }

    if (form.score !== null && form.score !== undefined && form.score !== "") {
      updateData.score = Number(form.score);
    }

    if (form.result && form.result !== "") {
      updateData.result = form.result;
    }

    // 数据完整性检查
    if (Object.keys(updateData).length === 0) {
      ElMessage.error("没有可更新的数据");
      return;
    }

    if (form.score !== null && form.score !== undefined && form.score !== "") {
      updateData.score = Number(form.score);
    }

    if (form.result && form.result !== "") {
      updateData.result = form.result;
    }

    // 数据完整性检查
    if (Object.keys(updateData).length === 0) {
      ElMessage.error("没有可更新的数据");
      return;
    }

    // 调用更新API
    const result = await updateLectureRecord(currentEditId.value, updateData);

    if (result.success) {
      ElMessage.success("记录更新成功");
      editDialogVisible.value = false;

      // 自动刷新列表数据
      await fetchLectureData(
        pagination.value.current,
        pagination.value.pageSize,
        searchKeyword.value
      );
    } else {
      // 错误信息已在 updateLectureRecord 中处理
      console.error("更新失败:", result.message);
    }
  } catch (error) {
    console.error("更新记录失败:", error);
    ElMessage.error("更新失败，请重试");
  } finally {
    editSubmitting.value = false;
  }
};

// 关闭编辑对话框
const handleEditDialogClose = () => {
  editDialogVisible.value = false;
  currentEditId.value = null;

  // 清空编辑表单
  editForm.value = {
    applicationDate: "",
    applicant: "",
    employeeId: "",
    department: "",
    course: "",
    area: "",
    shift: "",
    lectureDate: "",
    score: null,
    result: "",
  };
};

// 确认删除记录
const confirmDelete = async (record) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除申请人"${record.applicant}"的培训记录吗？`,
      "删除确认",
      {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        type: "warning",
      }
    );

    // 执行删除
    const result = await deleteLectureRecord(record.id);
    if (result.success) {
      ElMessage.success("删除成功");
    }
  } catch (error) {
    if (error !== "cancel") {
      console.error("删除失败:", error);
      ElMessage.error("删除失败");
    }
  }
};

// 返回功能
const goBack = () => {
  // 返回到Dashboard页面
  router.push({
    name: "Dashboard",
  });
};

// 组件卸载时清理所有定时器
onUnmounted(() => {
  if (refreshTimer) {
    clearTimeout(refreshTimer);
    refreshTimer = null;
  }
  if (submitTimer) {
    clearTimeout(submitTimer);
    submitTimer = null;
  }
  if (exportTimer) {
    clearTimeout(exportTimer);
    exportTimer = null;
  }
  if (searchTimer) {
    clearTimeout(searchTimer);
    searchTimer = null;
  }
});
</script>

<style scoped>
@import "@/style/general.css";
/* 全局隐藏所有滚动条 */
* {
  scrollbar-width: none !important; /* Firefox */
  -ms-overflow-style: none !important; /* IE 和 Edge */
}

*::-webkit-scrollbar {
  display: none !important; /* Chrome, Safari 和 Opera */
}

/* 确保深层组件也隐藏滚动条 */
:deep(*) {
  scrollbar-width: none !important; /* Firefox */
  -ms-overflow-style: none !important; /* IE 和 Edge */
}

:deep(*::-webkit-scrollbar) {
  display: none !important; /* Chrome, Safari 和 Opera */
}

/* 隐藏滚动条样式 */
.dashboard-container {
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE 和 Edge */
}

.dashboard-container::-webkit-scrollbar {
  display: none; /* Chrome, Safari 和 Opera */
}

/* 全局隐藏滚动条 */
:deep(*) {
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE 和 Edge */
}

:deep(*::-webkit-scrollbar) {
  display: none; /* Chrome, Safari 和 Opera */
}

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
  gap: 10px;
  align-items: center;
}

.placeholder {
  flex: 0 0 auto;
  width: 120px; /* 与返回按钮宽度保持平衡 */
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

.form-section,
.detail-section {
  background: rgba(255, 255, 255, 0.12);
  border-radius: 15px;
  padding: 25px;
  backdrop-filter: blur(15px);
  border: 1px solid rgba(255, 255, 255, 0.25);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  margin-bottom: 25px;
  animation: slideInUp 0.8s ease-out;
}

@keyframes slideInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.section-header {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  justify-content: space-between;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.section-icon {
  color: #60d9fa;
  font-size: 18px;
  margin-right: 8px;
}

.section-title {
  color: black;
  font-size: 18px;
  font-weight: bold;
  flex: 1;
}

.export-btn {
  background: #3875c5;
  border: none;
  border-radius: 8px;
  box-shadow: 0 4px 15px rgba(6, 182, 212, 0.3);
  transition: all 0.3s ease;
}

.export-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(56, 117, 197, 0.4);
}

.form-container {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  padding: 25px;
  border: 1px solid rgba(255, 255, 255, 0.15);
}

.form-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 5px;
  margin-bottom: 20px;
}

.form-field {
  margin-bottom: 0;
}

:deep(.el-form-item__label) {
  color: black !important;
  font-weight: 500;
}

:deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

:deep(.el-input__wrapper:hover) {
  border-color: rgba(96, 217, 250, 0.5);
  box-shadow: 0 0 15px rgba(96, 217, 250, 0.2);
}

:deep(.el-input__wrapper.is-focus) {
  border-color: #60d9fa;
  box-shadow: 0 0 20px rgba(96, 217, 250, 0.3);
}

:deep(.el-input__inner) {
  color: black;
  background: transparent;
}

:deep(.el-input__inner::placeholder) {
  color: rgba(255, 255, 255, 0.5);
}

/* 搜索框样式 */
:deep(.header-actions .el-input__wrapper) {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.submit-section {
  text-align: right;
  margin-top: 20px;
}

.submit-btn {
  background: #3875c5;
  border: none;
  border-radius: 8px;
  padding: 12px 30px;
  font-size: 16px;
  font-weight: 600;
  box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
  transition: all 0.3s ease;
}

.submit-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(56, 117, 197, 0.4);
}

/* Element Plus 按钮样式覆盖 */
:deep(.el-button) {
  background: rgba(255, 255, 255, 0.1) !important;
  border: 1px solid rgba(255, 255, 255, 0.3) !important;
  color: white !important;
  transition: all 0.3s ease !important;
}

:deep(.el-button.is-loading) {
  background: rgba(255, 255, 255, 0.05) !important;
  border-color: rgba(255, 255, 255, 0.2) !important;
  cursor: not-allowed !important;
}

:deep(.el-button.is-disabled) {
  background: rgba(255, 255, 255, 0.05) !important;
  border-color: rgba(255, 255, 255, 0.1) !important;
  color: rgba(255, 255, 255, 0.3) !important;
  cursor: not-allowed !important;
}

:deep(.el-button--success),
:deep(.el-button--danger),
:deep(.el-button--primary) {
  background: #3875c5 !important;
  border: none !important;
}

:deep(.el-button--success.is-loading),
:deep(.el-button--primary.is-loading) {
  background: #3875c5 !important;
}

/* 顶部返回/刷新自定义按钮统一填充色 */
.custom-btn :deep(.el-button__text),
.custom-btn {
  background: #3875c5 !important;
  border: none !important;
}

.table-container {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  padding: 15px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  width: 100%;
  overflow-x: auto;
  max-width: 100%;
  box-sizing: border-box;
}

/* 隐藏表格滚动条 */
.table-container {
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE 和 Edge */
}

.table-container::-webkit-scrollbar {
  display: none; /* Chrome, Safari 和 Opera */
}

/* 表格样式 */

.lecture-table {
  width: 100% !important;
  background: rgb(56, 117, 197) !important;
  border-radius: 8px !important;
  overflow: hidden !important;
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
  right: -4px;
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

/* 分页器样式 */
:deep(.el-pagination .el-pager li.is-active) {
  background: linear-gradient(45deg, #3875c5, #3875c5) !important;
  color: white !important;
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 20px;
  padding: 15px 0;
}

:deep(.el-pagination) {
  --el-pagination-bg-color: transparent;
  --el-pagination-text-color: black;
  --el-pagination-border-radius: 6px;
}

:deep(.el-pagination .el-pager li) {
  background: rgba(255, 255, 255, 0.1);
  color: black;
  border: 1px solid rgba(255, 255, 255, 0.2);
  margin: 0 2px;
}

:deep(.el-pagination .el-pager li:hover) {
  background: rgba(255, 255, 255, 0.2);
}

:deep(.el-pagination .el-pager li.is-active) {
  background: #60d9fa;
  color: black;
}

:deep(.el-pagination .btn-prev),
:deep(.el-pagination .btn-next) {
  background: rgba(255, 255, 255, 0.1);
  color: black;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

:deep(.el-pagination .btn-prev:hover),
:deep(.el-pagination .btn-next:hover) {
  background: rgba(255, 255, 255, 0.2);
}

:deep(.el-pagination .el-select .el-input__wrapper) {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
}

/* 分页组件文字颜色优化 */
:deep(.el-pagination .el-pagination__total) {
  color: black !important;
  font-weight: 500;
}

:deep(.el-pagination .el-pagination__jump) {
  color: black !important;
}

:deep(.el-pagination .el-pagination__editor) {
  color: black !important;
}

:deep(.el-pagination .el-pagination__classifier) {
  color: black !important;
}

:deep(.el-pagination .el-pagination__sizes .el-select) {
  color: black !important;
}

:deep(.el-pagination .el-pagination__sizes .el-select .el-input__inner) {
  color: black !important;
  background: rgba(255, 255, 255, 0.1) !important;
}

:deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

:deep(.el-table) {
  background: transparent;
  color: white;
  width: 100% !important;
  table-layout: fixed;
}

:deep(.el-table .el-table__header-wrapper) {
  position: sticky;
  top: 0;
  z-index: 10;
}

:deep(.el-table .el-table__header-wrapper) {
  position: sticky;
  top: 0;
  z-index: 10;
  background: transparent !important;
}

:deep(.el-table .el-table__body-wrapper) {
  background: rgb(198, 226, 255) !important;
}

:deep(.el-table__header) {
  background: rgb(56, 117, 197) !important;
}

:deep(.el-table th) {
  background: rgb(56, 117, 197) !important;
  color: white !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.3) !important;
  font-weight: 600 !important;
}

:deep(.el-table td) {
  border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
  background: rgb(198, 226, 255) !important;
  color: #3875c5 !important;
}

:deep(.el-table__row td) {
  background: rgb(198, 226, 255) !important;
  color: #3875c5 !important;
}

:deep(.el-table__row:hover td) {
  background: rgb(198, 226, 255) !important;
  color: #3875c5 !important;
}

:deep(.el-table--striped .el-table__body tr.el-table__row--striped td) {
  background: rgb(198, 226, 255) !important;
  color: #3875c5 !important;
}

:deep(.el-table tbody tr td) {
  background: rgb(198, 226, 255) !important;
  color: #3875c5 !important;
}

/* 强制覆盖 Element Plus 表格的白色背景 */
:deep(.el-table__body) {
  background: rgba(30, 58, 138, 0.2) !important;
}

:deep(.el-table__empty-block) {
  background: rgba(30, 58, 138, 0.2) !important;
}

:deep(.el-table__empty-text) {
  color: white !important;
}

.lecture-table {
  width: 100% !important;
}

/* 编辑对话框样式（白底黑字） */
:deep(.el-dialog) {
  background: #ffffff;
  border-radius: 15px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

:deep(.el-dialog__header) {
  background: #ffffff;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 15px 15px 0 0;
  padding: 20px 25px;
}

:deep(.el-dialog__title) {
  color: #000000;
  font-size: 18px;
  font-weight: 600;
}

:deep(.el-dialog__headerbtn .el-dialog__close) {
  color: rgba(0, 0, 0, 0.6);
  font-size: 20px;
}

:deep(.el-dialog__headerbtn .el-dialog__close:hover) {
  color: #000000;
}

:deep(.el-dialog__body) {
  padding: 25px;
  background: #ffffff;
}

:deep(.el-dialog__footer) {
  background: #ffffff;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 0 0 15px 15px;
  padding: 15px 25px;
}

/* 编辑表单样式（白底黑字） */
.edit-form :deep(.el-form-item__label) {
  color: #000000 !important;
  font-weight: 500;
}

.edit-form :deep(.el-input__wrapper) {
  background: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.15);
  border-radius: 8px;
}

.edit-form :deep(.el-input__wrapper:hover) {
  border-color: rgba(56, 117, 197, 0.4);
  box-shadow: 0 0 0 2px rgba(56, 117, 197, 0.08);
}

.edit-form :deep(.el-input__wrapper.is-focus) {
  border-color: #3875c5;
  box-shadow: 0 0 0 2px rgba(56, 117, 197, 0.15);
}

.edit-form :deep(.el-input__inner) {
  color: #000000;
  background: #ffffff;
}

.edit-form :deep(.el-input__inner::placeholder) {
  color: rgba(0, 0, 0, 0.4);
}

/* 数字输入框样式 */
.edit-form :deep(.el-input-number) {
  width: 100%;
}

.edit-form :deep(.el-input-number .el-input__wrapper) {
  background: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.15);
}

.edit-form :deep(.el-input-number .el-input__inner) {
  color: #000000;
  background: #ffffff;
}

/* 输入框前后缀图标与下拉箭头为黑色 */
.edit-form :deep(.el-input__prefix),
.edit-form :deep(.el-input__suffix) {
  color: #000000;
}

.edit-form :deep(.el-select .el-select__caret) {
  color: #000000;
}

/* 数字输入框增减按钮图标与背景 */
.edit-form :deep(.el-input-number__decrease),
.edit-form :deep(.el-input-number__increase) {
  color: #000000;
  background: #ffffff;
  border-color: rgba(0, 0, 0, 0.1);
}

/* 选择器样式 */
.edit-form :deep(.el-select .el-input__wrapper) {
  background: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.15);
}

.edit-form :deep(.el-select .el-input__inner) {
  color: #000000;
  background: #ffffff;
}

/* 日期选择器样式 */
.edit-form :deep(.el-date-editor.el-input) {
  width: 100%;
}

.edit-form :deep(.el-date-editor .el-input__wrapper) {
  background: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.15);
}

.edit-form :deep(.el-date-editor .el-input__inner) {
  color: #000000;
  background: #ffffff;
}

/* 对话框按钮样式 */
.dialog-footer :deep(.el-button) {
  background: rgba(255, 255, 255, 0.1) !important;
  border: 1px solid rgba(255, 255, 255, 0.3) !important;
  color: white !important;
  border-radius: 8px;
  padding: 10px 20px;
  font-weight: 500;
}

.dialog-footer :deep(.el-button:hover) {
  background: rgba(255, 255, 255, 0.2) !important;
  border-color: rgba(255, 255, 255, 0.5) !important;
}

.dialog-footer :deep(.el-button--primary) {
  background: #3875c5 !important;
  border: none !important;
}

.dialog-footer :deep(.el-button--primary:hover) {
  background: linear-gradient(45deg, #0891b2, #0284c7) !important;
  transform: translateY(-1px);
  box-shadow: 0 4px 15px rgba(6, 182, 212, 0.3);
}

/* 下拉选项样式优化 */
:deep(.el-select-dropdown) {
  background: linear-gradient(135deg, #1e3a8a 0%, #3730a3 100%) !important;
  border: 1px solid rgba(255, 255, 255, 0.3) !important;
  border-radius: 8px !important;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3) !important;
}

:deep(.el-select-dropdown .el-select-dropdown__item) {
  color: white !important;
  background: transparent !important;
  transition: all 0.3s ease !important;
}

:deep(.el-select-dropdown .el-select-dropdown__item:hover) {
  background: rgba(255, 255, 255, 0.1) !important;
  color: #60d9fa !important;
}

:deep(.el-select-dropdown .el-select-dropdown__item.selected) {
  background: rgba(96, 217, 250, 0.2) !important;
  color: #60d9fa !important;
  font-weight: 600 !important;
}

/* 日期选择器下拉面板样式 */
:deep(.el-picker-panel) {
  background: linear-gradient(135deg, #1e3a8a 0%, #3730a3 100%) !important;
  border: 1px solid rgba(255, 255, 255, 0.3) !important;
  border-radius: 8px !important;
  color: white !important;
}

:deep(.el-picker-panel .el-picker-panel__body) {
  background: transparent !important;
}

:deep(.el-picker-panel .el-date-picker__header) {
  color: white !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2) !important;
}

:deep(.el-picker-panel .el-picker-panel__content) {
  background: transparent !important;
}

:deep(.el-date-table td) {
  color: rgba(255, 255, 255, 0.8) !important;
}

:deep(.el-date-table td.available:hover) {
  background: rgba(96, 217, 250, 0.2) !important;
  color: #60d9fa !important;
}

:deep(.el-date-table td.current) {
  background: #60d9fa !important;
  color: #1e3a8a !important;
}

:deep(.el-time-panel) {
  background: linear-gradient(135deg, #1e3a8a 0%, #3730a3 100%) !important;
  border: 1px solid rgba(255, 255, 255, 0.3) !important;
}

:deep(.el-time-spinner__item) {
  color: white !important;
}

:deep(.el-time-spinner__item:hover) {
  background: rgba(255, 255, 255, 0.1) !important;
}

/* 禁用字段样式 */
.edit-form :deep(.el-input.is-disabled .el-input__wrapper) {
  background: #ffffff !important;
  border: 1px solid rgba(0, 0, 0, 0.1) !important;
  cursor: not-allowed !important;
}

.edit-form :deep(.el-input.is-disabled .el-input__inner) {
  color: #000000 !important;
  cursor: not-allowed !important;
}

.edit-form :deep(.el-date-editor.is-disabled .el-input__wrapper) {
  background: #ffffff !important;
  border: 1px solid rgba(0, 0, 0, 0.1) !important;
  cursor: not-allowed !important;
}

.edit-form :deep(.el-date-editor.is-disabled .el-input__inner) {
  color: #000000 !important;
  cursor: not-allowed !important;
}

.edit-form :deep(.el-date-editor.is-disabled .el-input__prefix) {
  color: #000000 !important;
}
</style>
