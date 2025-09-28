# OfferChecker

一个“投递状态监控 + 邮件提醒”的小工具：定时查询你在各招聘网站的投递进度，有变化就发邮件通知。

当前支持：
- 网易雷火（网页端接口）
- 米哈游
- 网易互娱（部分支持：该站点不直接显示状态，笔试和面试的状态应该可以获取，再之后的状态目前不支持（没见过）
- MokaHR（以鹰角为例，其他使用 Moka 的公司也可尝试）

> 说明：由于各站点登录鉴权不同，本工具通过“请求头 headers”来复用你的登录态（例如 Cookie 或 Authorization）。

---

## 一、快速开始（不需要改代码）

1) 安装 Python 依赖

```bash
pip install -r requirements.txt
```

2) 准备配置文件

- 复制示例配置为正式配置：
    - 将 `config.example.json` 复制为 `config.json`

- 填写邮件通知（以 QQ 邮箱为例）：
    - 开通“SMTP服务”，获取授权码（不是登录密码）
    - 配置示例：
        ```json
        "email": {
            "smtp_server": "smtp.qq.com",
            "sender": "你的邮箱",
            "password": "你的SMTP授权码",
            "receiver": "接收通知的邮箱"
        }
        ```

- 填写各站点登录凭据（统一放在公司条目的 `headers`）：
    - Cookie：在浏览器登录目标网站后，打开开发者工具（F12）→ Network，复制请求头里的整串 `Cookie` 到 `headers.Cookie`
    - Authorization：若站点使用 Bearer Token，则填到 `headers.Authorization`

3) 运行

```bash
python main.py
```

程序会在配置的工作时段内定时查询，一旦某家公司的投递状态发生变化，会给你发邮件提醒。

---

## 二、配置说明

配置文件为 `config.json`，关键字段：

- companies：要监控的公司列表。每个公司至少包含：
    - name：公司名称（用于记录和提示）
    - provider：数据来源（见下方“支持站点与示例”）
    - headers：请求头（用于登录态），至少包含 Cookie 或 Authorization
    - 可选 position_id：如果有多个投递记录，可指定只关注其中一个
    - 可选 extra：放该站点特有的额外配置（见下方示例）

- WORK_HOURS：工作时段（24 小时制），只在该时段内进行轮询
    - 例如：`{"start_hour": 10, "end_hour": 20}` 表示每天 10:00 至 20:00 查询

- sleep_seconds：轮询间隔（秒）。处于工作时段内，每轮检查后休眠的时长。

- logging：日志输出（可选）。支持控制台、文件或同时输出：
    ```json
    "logging": {
        "console_enabled": true,
        "file_enabled": true,
        "file": "monitor.log",
        "level": "INFO",
        "format": "%(asctime)s - %(levelname)s - %(message)s"
    }
    ```
    - 仅控制台：`file_enabled=false`
    - 仅文件：`console_enabled=false`
    - 同时输出：两者都为 `true`
    - 两者都为 `false`：完全禁用日志（不打印、不写文件）

状态文件 `last_state.json` 会保存上一轮状态，用于判断是否“发生了变化”。你也可以删除它来“重置已读”。

---

## 三、支持站点与配置示例

下方仅展示每个站点最关键的配置项，完整结构请参考 `config.example.json`。

1) 网易雷火（netease_leihuo）

```json
{
    "name": "网易雷火",
    "provider": "netease_leihuo",
    "headers": { "Cookie": "从浏览器复制的整串 Cookie" }
}
```

2) 米哈游（mihoyo）

```json
{
    "name": "米哈游",
    "provider": "mihoyo",
    "headers": { "Authorization": "Bearer <你的token>" }
}
```

3) 网易互娱（netease_huyu，部分支持）

```json
{
    "name": "网易互娱",
    "provider": "netease_huyu",
    "headers": { "Cookie": "从浏览器复制的整串 Cookie（含 SESSION）" }
}
```

4) MokaHR（mokahr，以鹰角为例）

```json
{
    "name": "鹰角",
    "provider": "mokahr",
    "headers": { "Cookie": "connect.sid=...; moka-token=...; ..." },
    "extra": {
        "request_body": { "orgId": "hypergryph", "siteId": 26326 }
    }
}
```

> 提示：MokaHR 站点需要两部分：
> - Cookie：复制浏览器里的整串 Cookie 到 `headers.Cookie`
> - orgId/siteId：可在浏览器开发者工具 Network 中找到对应请求的 Body 参数

---

## 四、常见问题（FAQ）

- 邮件发不出去？
    - 多为 SMTP 未开通或授权码错误；QQ 邮箱注意使用 465 端口且用授权码
- 提示未登录或 401/403？
    - 一般是 Cookie 过期或 Token 无效，重新登录站点并复制新的请求头
- 总是显示“无有效投递”？
    - 你可能没有任何有效投递记录，或该站点的接口返回结构变更（可稍后再试）
- 如何停止提醒？
    - 直接停止程序；或临时将 `WORK_HOURS` 设为一个不可能命中的时段
- 日志太多怎么办？
    - 在 `logging` 中把 `console_enabled` 与 `file_enabled` 都设为 `false` 即可彻底关闭

---

## 五、可选：扩展新网站（给开发者）

如果你会写 Python，并想自己扩展新的站点：
1. 在 `monitors/` 下新增一个模块，注册为 provider
2. 在 `config.json` 的公司条目里写上你的 provider 名称
3. 给出该站点需要的 `headers`（和可选 `extra`）

欢迎提交 PR 改进或新增站点支持。



