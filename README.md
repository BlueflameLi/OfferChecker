# OfferChecker

查询你的投递状态，如果变化了就发邮件通知你  
Deepseek 写的，凑合能用，支持以下几个
- 网易雷火(绿通车之类的特殊情况，网页端接口查不到，微信的接口比较麻烦，一般人也不好拿cookie，暂不支持)
- 米哈游  
- 部分支持网易互娱（这玩意儿不是直接显示状态的，比较复杂）  
- 鹰角等MokaHR的，不过没测试过其他的
    - 需要自行看一下这个接口的请求数据 `https://app.mokahr.com/api/outer/ats-apply/personal-center/applications`
    - 鹰角的是{ "orgId": "hypergryph","siteId": 26326}
- 未来可能支持腾讯，那个也比较麻烦


## 日志输出

支持将日志输出到控制台、文件，或二者同时输出。默认二者同时开启。

在 `config.json` 顶层添加（或使用示例中的默认值）：

```json
"logging": {
    "console_enabled": true,
    "file_enabled": true,
    "file": "monitor.log",
    "level": "INFO",
    "format": "%(asctime)s - %(levelname)s - %(message)s"
}
```

- 仅输出到控制台：设置 `file_enabled` 为 `false`
- 仅输出到文件：设置 `console_enabled` 为 `false`
- 两者同时输出：两者都为 `true`
- 若两者都为 `false`，将完全禁用日志输出（不写文件、不打印控制台）

