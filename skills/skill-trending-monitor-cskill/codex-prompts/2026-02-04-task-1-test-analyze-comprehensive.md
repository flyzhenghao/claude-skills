# Codex Prompt: 为 analyze_comprehensive.py 添加单元测试

**任务 ID**: Task #1
**生成时间**: 2026-02-04 14:30
**依赖**: 无

---

## 任务目标

为 `scripts/analyze_comprehensive.py` 编写完整的单元测试，将测试覆盖率从 **11%** 提高到 **70%+**。

---

## 背景信息

### 项目架构
```
skill-trending-monitor-cskill/
├── scripts/
│   ├── analyze_comprehensive.py  # 主编排器（266 行，目标文件）
│   ├── analyze_*.py              # 各分析模块
│   ├── fetch_*.py                # 数据获取模块
│   └── parse_*.py                # 数据解析模块
├── tests/
│   ├── test_config_loader.py     # 参考：现有测试风格
│   ├── test_fetch.py
│   └── test_dependencies.py
└── assets/
    ├── config.json               # 基础配置
    └── filters.json              # Profile 配置
```

### 相关文件
- `scripts/analyze_comprehensive.py`: 被测试的主模块
- `tests/test_config_loader.py`: 现有测试参考（测试风格示例）
- `assets/config.json`: 配置文件结构参考
- `assets/filters.json`: Profile 结构参考

### 技术栈
- Python 3.13
- pytest
- pandas
- 使用 mock/patch 模拟外部依赖

---

## 具体需求

### 功能需求

1. **测试 `_read_json()` 函数**
   - 正常读取 JSON 文件
   - 文件不存在时抛出异常
   - JSON 格式错误时抛出异常

2. **测试 `load_config()` 函数**
   - 默认路径加载
   - 自定义路径加载
   - 配置文件不存在时的行为

3. **测试 `_strip_metadata()` 函数**
   - 移除以 `_` 开头的键
   - 递归处理嵌套字典
   - 保留非 `_` 开头的键

4. **测试 `_deep_merge()` 函数**
   - 简单合并
   - 嵌套字典合并
   - 列表替换（非合并）

5. **测试 `load_profile()` 函数**
   - 加载已存在的 profile
   - 加载不存在的 profile 时抛出 ValueError

6. **测试 `_apply_profile()` 函数**
   - Profile 应用到配置
   - 部分 section 存在时的合并
   - 空 profile 不影响配置

### 技术要求
- 使用 `pytest` 框架
- 使用 `tmp_path` fixture 创建临时文件
- 使用 `unittest.mock.patch` 模拟外部依赖
- 每个测试函数独立，不依赖执行顺序
- 遵循现有 `test_config_loader.py` 的风格

### 质量标准
- [ ] 测试覆盖率 >= 70%
- [ ] 所有测试通过 `pytest tests/test_analyze_comprehensive.py -v`
- [ ] 无 flaky tests（每次运行结果一致）
- [ ] 测试函数命名清晰：`test_<function>_<scenario>`

---

## 实现指导

### 关键步骤

1. 创建 `tests/test_analyze_comprehensive.py`
2. 导入被测模块：
   ```python
   import sys
   from pathlib import Path
   sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
   from analyze_comprehensive import (
       _read_json, load_config, _strip_metadata,
       _deep_merge, load_profile, _apply_profile
   )
   ```
3. 为每个函数编写正常情况和边界情况测试
4. 使用 fixtures 减少重复代码

### 注意事项
- ⚠️ `analyze_comprehensive.py` 依赖其他模块（fetch_*, parse_* 等），测试时需 mock
- ⚠️ 不要测试 `main()` 函数的完整流程（那是集成测试）
- ⚠️ 使用 `tmp_path` 而非硬编码路径

### 可能的陷阱
- ❌ 依赖真实 `assets/config.json`：使用 `tmp_path` 创建临时配置
- ❌ 测试执行顺序依赖：每个测试应独立
- ❌ 直接调用 API：mock 所有外部调用

---

## 验证方法

### 单元测试
```bash
cd skill-trending-monitor-cskill
source .venv/bin/activate
pytest tests/test_analyze_comprehensive.py -v --cov=scripts/analyze_comprehensive --cov-report=term-missing
```

### 覆盖率检查
```bash
pytest tests/test_analyze_comprehensive.py --cov=scripts/analyze_comprehensive --cov-fail-under=70
```

---

## 预期输出

### 代码文件
- `tests/test_analyze_comprehensive.py`: 完整的测试文件（预计 150-200 行）

### 测试覆盖
| 函数 | 当前覆盖 | 目标覆盖 |
|------|---------|---------|
| _read_json | 0% | 90% |
| load_config | 20% | 80% |
| _strip_metadata | 0% | 100% |
| _deep_merge | 0% | 100% |
| load_profile | 10% | 90% |
| _apply_profile | 5% | 80% |

---

## 时间预估

- **编写测试**: 30 分钟
- **调试修复**: 10 分钟
- **验证覆盖率**: 5 分钟
- **总计**: 45 分钟

---

## 提交规范

**Commit Message 格式**:
```
test(analyze_comprehensive): add unit tests for core functions

- Add tests for _read_json, load_config, _strip_metadata
- Add tests for _deep_merge, load_profile, _apply_profile
- Target coverage: 70%+ (from 11%)

Implements: Task #1
```

---

## 参考资料

- 现有测试风格: `tests/test_config_loader.py`
- pytest fixtures: https://docs.pytest.org/en/stable/fixture.html
- unittest.mock: https://docs.python.org/3/library/unittest.mock.html
