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

