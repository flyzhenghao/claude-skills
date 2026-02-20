# Codex Prompt: 为 fetch_github_stars.py 添加单元测试

**任务 ID**: Task #3
**生成时间**: 2026-02-04 14:30
**依赖**: 无

---

## 任务目标

为 `scripts/fetch_github_stars.py` 编写完整的单元测试，将测试覆盖率从 **21%** 提高到 **75%+**。

---

## 背景信息

### 项目架构
```
skill-trending-monitor-cskill/
├── scripts/
│   └── fetch_github_stars.py   # GitHub API 交互（159 行，目标文件）
├── tests/
│   ├── test_fetch.py           # 现有 fetch 测试参考
│   └── (新建 test_fetch_github_stars.py)
└── assets/
    └── config.json             # 包含 GitHub token 配置
```

### 相关文件
- `scripts/fetch_github_stars.py`: 被测试的 GitHub Stars 获取模块
- `tests/test_fetch.py`: 现有 fetch 测试参考

### 技术栈
- Python 3.13
- pytest
- requests (HTTP 客户端)
- unittest.mock (模拟 API 响应)

### 主要函数

```python
def fetch_star_history(repo_url: str, token: str = None) -> List[Dict]
def fetch_repo_metadata(repo_url: str, token: str = None) -> Dict
def parse_github_url(url: str) -> Tuple[str, str]  # (owner, repo)
def get_rate_limit_status(token: str = None) -> Dict
```

---

## 具体需求

### 功能需求

1. **测试 `parse_github_url()` 函数**
   - 正常 URL: `https://github.com/owner/repo`
   - 带 .git 后缀: `https://github.com/owner/repo.git`
   - SSH URL: `git@github.com:owner/repo.git`
   - 无效 URL 抛出异常

2. **测试 `fetch_star_history()` 函数**
   - 成功获取 star 历史（mock API 响应）
   - API 返回空列表
   - API 返回 404（仓库不存在）
   - API 返回 403（rate limit）
   - 网络错误处理

3. **测试 `fetch_repo_metadata()` 函数**
   - 成功获取仓库元数据
   - 仓库不存在（404）
   - 仓库为私有（401/403）

4. **测试 `get_rate_limit_status()` 函数**
   - 成功获取限额状态
   - 无 token 时的限额

5. **测试认证逻辑**
   - 有 token 时添加 Authorization header
   - 无 token 时不添加 header

### 技术要求
- 使用 `pytest` 框架
- 使用 `unittest.mock.patch` 模拟 `requests.get`
- 使用 `responses` 库或 `requests_mock` 作为备选
- 不发送真实 HTTP 请求
- 每个测试函数独立

### 质量标准
- [ ] 测试覆盖率 >= 75%
- [ ] 所有测试通过
- [ ] 无真实 API 调用
- [ ] 错误场景全面覆盖

---

## 实现指导

### 关键步骤

1. 创建 `tests/test_fetch_github_stars.py`
2. 导入被测模块：
   ```python
   import sys
   from pathlib import Path
   sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
   from fetch_github_stars import (
       parse_github_url, fetch_star_history,
       fetch_repo_metadata, get_rate_limit_status
   )
   ```
3. Mock requests.get：
   ```python
   from unittest.mock import patch, Mock

   @patch('fetch_github_stars.requests.get')
   def test_fetch_star_history_success(mock_get):
       mock_response = Mock()
       mock_response.status_code = 200
       mock_response.json.return_value = [
           {"starred_at": "2026-01-01T00:00:00Z", "user": {"login": "alice"}}
       ]
       mock_get.return_value = mock_response

       result = fetch_star_history("https://github.com/owner/repo", "token")

       assert len(result) == 1
       mock_get.assert_called_once()
   ```

### 注意事项
- ⚠️ 绝对不能发送真实 API 请求
- ⚠️ 测试需覆盖分页逻辑（如果有）
- ⚠️ 注意 header 中的 token 格式

### 可能的陷阱
- ❌ 真实 API 调用：必须 mock requests.get
- ❌ 忘记测试错误码：403、404、500 都要测
- ❌ 忽略分页：如果 API 有分页，需测试

---

## 验证方法

### 单元测试
```bash
cd skill-trending-monitor-cskill
source .venv/bin/activate
pytest tests/test_fetch_github_stars.py -v --cov=scripts/fetch_github_stars --cov-report=term-missing
```

### 覆盖率检查
```bash
pytest tests/test_fetch_github_stars.py --cov=scripts/fetch_github_stars --cov-fail-under=75
```

---

## 预期输出

### 代码文件
- `tests/test_fetch_github_stars.py`: 完整的测试文件（预计 150-180 行）

### 测试覆盖
| 函数 | 当前覆盖 | 目标覆盖 |
|------|---------|---------|
| parse_github_url | 40% | 95% |
| fetch_star_history | 15% | 80% |
| fetch_repo_metadata | 10% | 75% |
| get_rate_limit_status | 0% | 70% |

---

## 时间预估

- **编写测试**: 25 分钟
- **调试修复**: 5 分钟
- **总计**: 30 分钟

---

## 提交规范

**Commit Message 格式**:
```
test(fetch_github_stars): add unit tests for GitHub API module

- Add tests for parse_github_url with various URL formats
- Add tests for fetch_star_history with mocked responses
- Add tests for error handling (404, 403, network errors)
- Target coverage: 75%+ (from 21%)

Implements: Task #3
```

---

## 参考资料

- unittest.mock: https://docs.python.org/3/library/unittest.mock.html
- pytest-requests-mock: https://pypi.org/project/pytest-requests-mock/
- GitHub API: https://docs.github.com/en/rest/activity/starring
