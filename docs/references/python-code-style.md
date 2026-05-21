# Python Code Style（模板偏好）

本文记录当前模板仓库的 Python 代码开发和 review 偏好。它不是跨项目协作宪章；从模板创建的新仓库可按自己的技术栈替换本文。

## Tooling

- 使用 `uv` 进行 Python 包管理和虚拟环境管理。
- 如需 Notebook 兼容，在 `.venv` 中安装 `ipykernel` 和 `ipywidgets`。
- Notebook 长循环使用 `tqdm` 展示进度。
- JSON 处理优先使用 `orjson`。
- 记录错误时优先使用 `logger.error`。
- 使用 Ruff 做格式化和 lint，`isort` 风格整理导入；使用 mypy 做静态检查；使用 pytest 做测试。

## Style And Formatting

- 遵循 PEP 8。
- 使用 4 空格缩进。
- 行宽控制在 88 字符左右。
- 函数和变量使用 snake_case，类使用 PascalCase，常量使用 UPPER_CASE。
- 使用有意义的变量名和函数名。
- 不使用 emoji 或伪 emoji 字符。

## Type Hints

- 函数签名必须写类型标注。
- 非必要不要使用 `Any` 逃生口。
- 可空类型使用 `Optional[T]` 或 `T | None`。
- 变更后应通过 mypy 检查。

## Imports And Dependencies

- 不使用 `from module import *`。
- 不在提交代码中使用 `sys.path.insert` / `sys.path.append` 等运行时路径注入；脚本、测试和工具入口必须通过 `pyproject.toml`、可安装 package 或明确的命令入口解决导入路径。
- 依赖应记录在 `pyproject.toml`。
- 导入顺序分为标准库、第三方、本地模块。

## Function And Class Design

- 一个函数只做一件事。
- 不使用可变默认参数。
- 参数尽量控制在 5 个以内。
- 尽量早返回，减少嵌套。
- 一个类只负责一类职责。
- 构造器中避免复杂逻辑。
- 简单数据容器优先使用 dataclass。
- 优先组合而不是继承。
- 非必要不要增加额外类方法。
- 计算型属性优先使用 `@property`。

## Error Handling

- 不要静默吞掉异常。
- bare `except:` 在 Python 中等同 `except BaseException`，禁止。
- 尽量捕获具体异常类型。
- 默认采用 fail-fast，不要为了"更稳"无依据地降级。
- 只有在边界校验、资源清理、取消控制或兼容层场景下，才允许保留必要的防御性逻辑。
- 不要用 `getattr(..., default)` / `dict.get(..., default)` 掩盖必需接口或必需字段缺失。
- 错误信息要可定位。

## Testing

- 新增函数和类应补充单元测试。
- 外部依赖必须 mock。
- 使用 Arrange-Act-Assert 结构。
- 不提交注释掉的测试。
- 自动化测试只覆盖代码、可执行入口、脚本行为、配置解析等会影响运行结果的对象。
- 禁止给文档、README、协作规则、skill 文案或中文措辞写字符串断言测试。文档质量通过人工 review、diff 审阅、链接检查或格式解析检查处理，不用脆弱测试锁死文字。

## Documentation Style

- 所有公开函数、类、方法都应有 docstring（不是只写注释）。
- docstring 说明参数、返回值和可能抛出的异常。
- 复杂逻辑可增加简短注释。
- 复杂函数的 docstring 应包含示例。

## Data And Storage

- 数据处理优先使用 `polars`，不要默认使用 `pandas`。
- 不要一次摄入过大的数据样本到上下文。
- 建表时优先使用合适的数据类型。
- 嵌套字段优先使用 `ARRAY` 等结构化类型，不要用 `TEXT` 硬塞。

## Security And Version Control

- 密钥、密码、令牌只能放在环境变量或 `.env`。
- 不要提交凭证或敏感信息。
- 不要打印包含密钥的 URL。
- 不要记录密码、Token、PII 等敏感数据。
- 提交信息应清晰描述改动。
- 不提交调试输出、断点、注释掉的废弃代码。
