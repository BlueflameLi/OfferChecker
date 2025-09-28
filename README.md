# OfferChecker

一个“投递状态监控 + 邮件提醒”的小工具：定时查询你在各招聘网站的投递进度，有变化就发邮件通知。
自动登录比较复杂，暂不支持，只能手动复制Cookie，不同网站Cookie有效时间不同，大部分应该都好几天都不会过期，但也有一天就过期的，比如米哈游  
当前支持：
- 网易雷火（网页端接口，绿通之类只能在微信上看的暂不支持）
- 米哈游
- 网易互娱（部分支持：互娱的状态解析很复杂，且有个字典，目前细的状态（一面、二面这种）只有面试支持，其他状态暂时只能支持到大的状态（笔试、录用审核））
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
    - 若日志文件路径不可写，程序会自动回退到控制台输出并打印警告。部署容器时请确保挂载的 `/config` 目录对容器用户具有写权限，可通过 `chown -R 1000:1000 <宿主目录>`（或使用 `:z` 标志）解决。

状态文件 `last_state.json` 会保存上一轮状态，用于判断是否“发生了变化”。你也可以删除它来“重置已读”。

> 环境变量覆盖：在容器或进程环境中可通过下列变量重定向文件位置
> - `CONFIG_PATH`：配置文件路径（默认 `config.json`）
> - `STATE_FILE_PATH`：状态缓存路径（默认 `last_state.json`）
> - `LOG_PATH`：默认日志文件路径（仍可在配置里覆盖）

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
    "headers": { "Authorization": "ats@开头" }
}
```

3) 网易互娱（netease_huyu，部分支持）

```json
{
    "name": "网易互娱",
    "provider": "netease_huyu",
    "headers": { "Cookie": "从浏览器复制的整串 Cookie" }
}
```

4) MokaHR（mokahr，以鹰角为例）

```json
{
    "name": "鹰角",
    "provider": "mokahr",
    "headers": { "Cookie": "从浏览器复制的整串 Cookie" },
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

---

## 六、Docker 部署

项目已提供官方 Docker 镜像构建流水线，推送到 `main` 分支会自动构建并发布到 **GitHub Container Registry**：

- 镜像地址：`ghcr.io/<你的 GitHub 用户名/组织>/<仓库名>`（例如本仓库为 `ghcr.io/blueflammeli/offerchecker`）
- 标签策略：
    - `latest`：`main` 分支最新一次提交
    - `<分支名>`：对应分支最新一次提交
    - `<tag>`：与仓库 tag 一致
    - `sha-<短提交号>`：精确提交版本

### 1. 拉取镜像

登录 GHCR（需要启用 `read:packages` 权限）：

```bash
echo <YOUR_GHCR_TOKEN> | docker login ghcr.io -u <YOUR_GITHUB_USERNAME> --password-stdin
```

随后拉取镜像：

```bash
docker pull ghcr.io/blueflammeli/offerchecker:latest
```

### 2. 运行容器

建议使用宿主目录挂载 `/config` 目录，配置、日志与状态文件都会存放在其中：

```bash
mkdir -p config
cp config.example.json config/config.json
```

运行容器：

```bash
docker run -d \
    --name offerchecker \
    -e TZ=Asia/Shanghai \
    -e CONFIG_PATH=/config/config.json \
    -e STATE_FILE_PATH=/config/last_state.json \
    -e LOG_PATH=/config/monitor.log \
    -v $(pwd)/config:/config \
    ghcr.io/blueflammeli/offerchecker:latest
```

- `CONFIG_PATH` 指向容器内的配置文件路径；通过挂载方式将宿主的 `config.json` 映射进去
- `STATE_FILE_PATH` 与 `LOG_PATH` 默认都位于 `/config` 目录下，和配置放在一起便于整体备份
- 若需要自定义日志策略，可在 `config.json` 的 `logging` 字段中调整
- `TZ` 默认为 `Asia/Shanghai`，可根据需要改成其他时区（例如 `UTC`）
- 容器默认以 root 用户运行，如需切换为其他用户可在 `docker run` 时追加 `--user <uid>:<gid>`，并确保挂载目录权限匹配

### 3. 使用自定义镜像名

如果你 fork 了仓库，可在仓库 Settings → Packages 查看自己的镜像地址。默认 workflow 会根据仓库路径自动生成小写镜像名，无需额外配置。

### 4. 使用 docker-compose

仓库提供了 `docker-compose.yml` 示例，方便一键启动与托管。使用前先准备配置目录：

```bash
mkdir -p config
cp config.example.json config/config.json
```

编辑 `config/config.json` 完成各站点与邮箱配置后，执行：

```bash
docker compose up -d
```

- 默认使用镜像 `ghcr.io/blueflammeli/offerchecker:latest`
- `/config` 挂载到宿主的 `./config` 目录，日志与状态文件也会保存在其中
- 可通过 `.env` 或直接修改 `docker-compose.yml` 来调整镜像标签、时区（`TZ`）或其他环境变量
- 若希望使用非 root 用户，可在 compose 文件中添加 `user: "<uid>:<gid>"` 并相应调整权限



