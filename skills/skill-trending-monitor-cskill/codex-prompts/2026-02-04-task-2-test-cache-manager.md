# Codex Prompt: 为 cache_manager.py 添加单元测试

**任务 ID**: Task #2
**生成时间**: 2026-02-04 14:30
**依赖**: 无

---

## 任务目标

为 `scripts/utils/cache_manager.py` 编写完整的单元测试，将测试覆盖率从 **13%** 提高到 **80%+**。

---

## 背景信息

### 项目架构
```
skill-trending-monitor-cskill/
├── scripts/
│   └── utils/
│       └── cache_manager.py    # 缓存管理器（148 行，目标文件）
├── tests/
│   └── (新建 test_cache_manager.py)
└── data/
    └── cache/                  # 默认缓存目录
        ├── metadata/           # 30天TTL
        └── security/           # 7天TTL
```

### 相关文件
- `scripts/utils/cache_manager.py`: 被测试的缓存模块
- `tests/test_config_loader.py`: 现有测试参考

### 技术栈
- Python 3.13
- pytest
- 文件系统操作（JSON 读写）
- datetime 和 timedelta

### CacheManager 类 API

```python
class CacheManager:
    def __init__(self, cache_dir: Optional[Path] = None)
    def get(self, key: str, cache_type: str = 'metadata') -> Optional[Any]
    def set(self, key: str, value: Any, cache_type: str = 'metadata') -> None
    def invalidate(self, key: str, cache_type: str = 'metadata') -> bool
    def cleanup_expired(self, cache_type: str = 'metadata') -> int
    def clear_all(self, cache_type: str = 'metadata') -> int
```

---

## 具体需求

### 功能需求

1. **测试 `__init__()` 初始化**
   - 默认路径创建
   - 自定义路径创建
   - 目录自动创建

2. **测试 `get()` 方法**
   - 获取存在且未过期的缓存
   - 获取不存在的缓存（返回 None）
   - 获取已过期的缓存（返回 None）
   - 不同 cache_type (metadata vs security)

3. **测试 `set()` 方法**
   - 正常设置缓存
   - 覆盖已存在的缓存
   - 不同 cache_type
   - 验证 JSON 格式正确

4. **测试 `invalidate()` 方法**
   - 删除存在的缓存（返回 True）
   - 删除不存在的缓存（返回 False）

5. **测试 `cleanup_expired()` 方法**
   - 清理过期项（返回清理数量）
   - 保留未过期项
   - 空目录不报错

6. **测试 `clear_all()` 方法**
   - 清空所有缓存（返回删除数量）
   - 空目录返回 0

7. **测试 TTL 逻辑**
   - metadata TTL = 30 天
   - security TTL = 7 天
   - 边界条件（刚好过期）

### 技术要求
- 使用 `pytest` 框架
- 使用 `tmp_path` fixture 作为临时缓存目录
- 使用 `freezegun` 或 `unittest.mock.patch` 模拟时间
- 每个测试函数独立

### 质量标准
- [ ] 测试覆盖率 >= 80%
- [ ] 所有测试通过
- [ ] 无文件系统污染（使用 tmp_path）
- [ ] 时间相关测试稳定（mock datetime）

---

## 实现指导

### 关键步骤

1. 创建 `tests/test_cache_manager.py`
2. 导入被测模块：
   ```python
   import sys
   from pathlib import Path
   sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts' / 'utils'))
   from cache_manager import CacheManager
   ```
3. 创建 fixture 用于临时缓存目录：
   ```python
   @pytest.fixture
   def cache(tmp_path):
       return CacheManager(cache_dir=tmp_path / 'cache')
   ```
4. 模拟时间用于 TTL 测试：
   ```python
   from unittest.mock import patch
   from datetime import datetime, timedelta

   @patch('cache_manager.datetime')
   def test_expired_cache(mock_datetime, cache):
       mock_datetime.now.return_value = datetime(2026, 2, 4)
       # ...
   ```

### 注意事项
- ⚠️ 必须使用 `tmp_path` 避免污染真实缓存目录
- ⚠️ 时间相关测试必须 mock datetime，否则会 flaky
- ⚠️ 测试文件系统操作时注意跨平台兼容性

### 可能的陷阱
- ❌ 使用真实缓存目录：必须用 `tmp_path`
- ❌ 依赖系统时间：必须 mock
- ❌ 测试间共享状态：每个测试用独立 cache fixture

---

## 验证方法

### 单元测试
```bash
cd skill-trending-monitor-cskill
source .venv/bin/activate
pytest tests/test_cache_manager.py -v --cov=scripts/utils/cache_manager --cov-report=term-missing
```

### 覆盖率检查
```bash
pytest tests/test_cache_manager.py --cov=scripts/utils/cache_manager --cov-fail-under=80
```

---

## 预期输出

### 代码文件
- `tests/test_cache_manager.py`: 完整的测试文件（预计 180-220 行）

### 测试覆盖
| 方法 | 当前覆盖 | 目标覆盖 |
|------|---------|---------|
| __init__ | 30% | 100% |
| get | 10% | 90% |
| set | 15% | 90% |
| invalidate | 0% | 90% |
| cleanup_expired | 0% | 85% |
| clear_all | 0% | 90% |

---

## 时间预估

- **编写测试**: 25 分钟
- **调试修复**: 5 分钟
- **总计**: 30 分钟

---

## 提交规范

**Commit Message 格式**:
```
test(cache_manager): add comprehensive unit tests

- Add tests for get, set, invalidate methods
- Add tests for cleanup_expired, clear_all
- Add TTL expiration tests with mocked datetime
- Target coverage: 80%+ (from 13%)

Implements: Task #2
```

---

## 参考资料

- pytest tmp_path: https://docs.pytest.org/en/stable/how-to/tmp_path.html
- unittest.mock: https://docs.python.org/3/library/unittest.mock.html
