# Cursor Stats Alfred Workflow

这是一个用于查看 Cursor 基于次数计费的统计信息的 Alfred workflow。

## 📦 安装

### 直接安装

点击下面的链接直接下载并安装：

**[⬇️ 下载 Cursor Stats.alfredworkflow](./Cursor-Stats.alfredworkflow)**

## 🛠️ 系统要求

- macOS
- Alfred 4+ (需要 Powerpack)
- Python 3.6+
- 已安装并登录 Cursor

## 🎯 使用方法

1. 在 Alfred 中输入关键词（默认为 `cursorstats`）
2. 查看显示的使用量统计信息
3. 选择相应项目执行操作或复制信息

## ⚙️ 自定义设置

安装后，您可以在 Alfred Preferences > Workflows > Cursor Stats 中自定义：

- **关键词设置**：修改触发关键词（默认：`cursorstats`）
- **缓存时间**：调整数据缓存时间（默认：60 秒）
- **货币显示**：选择货币格式（支持 USD, EUR, GBP, JPY, CNY 等）

## 🔧 故障排除

如果遇到问题，请检查：

1. **Cursor 登录状态**：确保 Cursor 已正确登录
2. **网络连接**：确保网络连接正常
3. **Python 环境**：确保 `python3` 命令可正常执行

### 常见问题

**Q: 项目是如何获取 Cursor 的认证信息的？**
A: 项目会自动从 Cursor 的本地数据库(`~/Library/Application Support/Cursor/User/globalStorage/state.vscdb`)中获取 认证信息，无需手动输入。

**Q: 显示"未找到 Cursor 认证信息"**
A: 请确保 Cursor 应用已登录，并重新启动 Alfred

**Q: 数据不更新**
A: 选择"刷新数据"选项强制更新，或检查网络连接

**Q: 无法显示使用量计费信息**
A: 使用量计费信息只在有相关数据时显示，如果您是免费用户可能不会显示此项

## 🛡️ 隐私说明

- 本 workflow 仅读取本地 Cursor 数据库中的认证信息
- 所有 API 请求直接发送到 Cursor 官方服务器
- 不收集、存储或传输任何个人数据
- 所有数据处理均在本地完成

## 📄 许可证

[MIT License](./LICENSE)

## ⭐ 支持项目

如果这个项目对您有帮助，请给个 Star ⭐️

---

**注意**: 本项目与 Cursor 官方无关，仅为第三方工具。使用前请确保遵守 Cursor 的服务条款。
