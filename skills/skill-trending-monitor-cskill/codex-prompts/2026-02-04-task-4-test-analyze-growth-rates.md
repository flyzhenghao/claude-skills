# Codex Prompt: 为 analyze_growth_rates.py 添加单元测试

**任务 ID**: Task #4
**生成时间**: 2026-02-04 14:30
**依赖**: 无

---

## 任务目标

为 `scripts/analyze_growth_rates.py` 编写完整的单元测试，将测试覆盖率从 **27%** 提高到 **75%+**。

---

## 背景信息

### 项目架构
```
skill-trending-monitor-cskill/
├── scripts/
│   └── analyze_growth_rates.py  # 增长率分析（153 行，目标文件）
├── tests/
│   └── (新建 test_analyze_growth_rates.py)
└── assets/
    └── config.json              # 阈值配置
```

### 相关文件
- `scripts/analyze_growth_rates.py`: 被测试的增长率分析模块
- `tests/test_recommendations.py`: 现有分析测试参考

### 技术栈
- Python 3.13
- pytest
- pandas
- numpy (数学计算)

### 主要函数

```python
def calculate_growth_rate(current: int, previous: int) -> float
def analyze_growth_rates(skills_df: pd.DataFrame, period_days: int = 7) -> pd.DataFrame
def classify_growth(rate: float, thresholds: Dict) -> str
def detect_anomalies(growth_rates: List[float]) -> List[int]
def get_trending_skills(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame
```

---

## 具体需求

### 功能需求

1. **测试 `calculate_growth_rate()` 函数**
   - 正常增长: (150, 100) → 0.5 (50%)
   - 负增长: (80, 100) → -0.2 (-20%)
   - 零增长: (100, 100) → 0.0
   - 从零增长: (100, 0) → 处理方式（inf 或特殊值）
   - 到零: (0, 100) → -1.0 (-100%)

2. **测试 `analyze_growth_rates()` 函数**
   - 正常 DataFrame 输入
   - 空 DataFrame
   - 缺少必要列时的行为
   - 不同 period_days 参数

3. **测试 `classify_growth()` 函数**
   - 爆发式增长 (rate > 1.0)
   - 高速增长 (0.5 < rate <= 1.0)
   - 稳定增长 (0.1 < rate <= 0.5)
   - 停滞 (-0.1 <= rate <= 0.1)
   - 衰退 (rate < -0.1)
   - 自定义阈值

4. **测试 `detect_anomalies()` 函数**
   - 检测异常高增长
   - 检测异常负增长
   - 正常数据无异常
   - 空列表

5. **测试 `get_trending_skills()` 函数**
   - 获取 Top N
   - N 大于数据量时
   - 按增长率排序

### 技术要求
- 使用 `pytest` 框架
- 使用 `pandas.testing.assert_frame_equal` 验证 DataFrame
- 测试边界条件（除零、空数据）
- 数学计算精度验证

### 质量标准
- [ ] 测试覆盖率 >= 75%
- [ ] 所有测试通过
- [ ] 数学计算精度正确（浮点数比较用 pytest.approx）
- [ ] 边界条件全面覆盖

---

## 实现指导

### 关键步骤

1. 创建 `tests/test_analyze_growth_rates.py`
2. 导入被测模块：
   ```python
   import sys
   from pathlib import Path
   import pandas as pd
   import pytest

   sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
   from analyze_growth_rates import (
       calculate_growth_rate, analyze_growth_rates,
       classify_growth, detect_anomalies, get_trending_skills
   )
   ```
3. 使用 pytest.approx 进行浮点数比较：
   ```python
   def test_calculate_growth_rate_normal():
       result = calculate_growth_rate(150, 100)
       assert result == pytest.approx(0.5, rel=1e-6)
   ```
4. 创建测试用 DataFrame fixture：
   ```python
   @pytest.fixture
   def sample_skills_df():
       return pd.DataFrame({
           'name': ['skill-a', 'skill-b', 'skill-c'],
           'stars_current': [150, 80, 100],
           'stars_previous': [100, 100, 100]
       })
   ```

### 注意事项
- ⚠️ 浮点数比较必须用 pytest.approx
- ⚠️ 除零情况必须处理（current / 0）
- ⚠️ pandas DataFrame 比较用专用方法

### 可能的陷阱
- ❌ 直接 `assert x == 0.5`：浮点数必须用 approx
- ❌ 忽略除零：(x, 0) 必须测试
- ❌ 假设 DataFrame 列存在：测试缺列情况

---

## 验证方法

### 单元测试
```bash
cd skill-trending-monitor-cskill
source .venv/bin/activate
pytest tests/test_analyze_growth_rates.py -v --cov=scripts/analyze_growth_rates --cov-report=term-missing
```

### 覆盖率检查
```bash
pytest tests/test_analyze_growth_rates.py --cov=scripts/analyze_growth_rates --cov-fail-under=75
```

---

## 预期输出

### 代码文件
- `tests/test_analyze_growth_rates.py`: 完整的测试文件（预计 150-180 行）

### 测试覆盖
| 函数 | 当前覆盖 | 目标覆盖 |
|------|---------|---------|
| calculate_growth_rate | 50% | 95% |
| analyze_growth_rates | 20% | 75% |
| classify_growth | 30% | 90% |
| detect_anomalies | 10% | 70% |
| get_trending_skills | 20% | 75% |

---

## 时间预估

- **编写测试**: 25 分钟
- **调试修复**: 5 分钟
- **总计**: 30 分钟

---

## 提交规范

**Commit Message 格式**:
```
test(analyze_growth_rates): add unit tests for growth analysis

- Add tests for calculate_growth_rate with edge cases
- Add tests for classify_growth with custom thresholds
- Add tests for detect_anomalies
- Add tests for get_trending_skills
- Target coverage: 75%+ (from 27%)

Implements: Task #4
```

---

## 参考资料

- pytest.approx: https://docs.pytest.org/en/stable/reference/reference.html#pytest-approx
- pandas.testing: https://pandas.pydata.org/docs/reference/testing.html
