# 首次上传与后续发布

## 仓库信息

- 地址：[RuneYang123/fitness-companion](https://github.com/RuneYang123/fitness-companion)。
- 公开联系邮箱：[runeyang123@outlook.com](mailto:runeyang123@outlook.com)。
- 仓库名：`fitness-companion`；界面展示名：`练得明白 · Fitness Companion`。
- 可选Topics：`agent-skills`、`fitness`、`nutrition`、`exercise`、`chinese`。

GitHub About可使用：

> Fitness Companion | A Chinese-language fitness skill for adults, tailoring training, nutrition, supplement choices, and sleep guidance to your goals, schedule, and equipment. Supports exercise tutorials, on-demand feedback, and portable plans for continuing across chats.

## 上传前

在本项目根目录执行：

```sh
python3 scripts/package.py --check --release
python3 -m unittest discover -s tests -v
python3 scripts/package.py --repository
```

使用`dist/fitness-companion-repository-v0.1.0.zip`准备源码仓库。将它解压到单独的干净位置，核对README、LICENSE、NOTICE、CONTRIBUTING、CHANGELOG、`.gitignore`、`.github/`、`docs/`、`scripts/`、`tests/`和`skills/`均完整；隐藏的`.github`目录也要保留。

不要从含私人资料的上层工作区整体提交。仓库包由白名单生成，不含私人方案、训练记录、封装记录、宣传稿和视频缓存。已有远端内容时先查看并合并，不能直接强制覆盖。

## 上传后

1. 确认仓库公开可访问、README图片与文件链接正常，且项目文件确实存在。
2. 查看Actions中的Validate Skill是否成功；本地检查通过不等于远端CI已经运行。
3. 从一个干净目录按README安装，开启一个新聊天试用；不同客户端需分别验证，不能用同一聊天试跑代替。
4. 核对[作者结尾](../skills/fitness-companion/references/plan-closing.md)中的仓库和邮箱。“已经开源发布”只在实际发布后作为状态说明，地址填写完成不等于已经上传。
5. 需要创建首个Release时，再使用版本`v0.1.0`，附独立Skill ZIP与对应SHA256校验值。首次上传源码不要求同时创建Release。

## 后续更新

先修改源码和相关示例，运行校验与测试；发布新版本时同步更新SKILL.md的版本号、更新记录与文档中的包名，然后重新生成两种包。安装目录是副本，已有本地改动先比较再同步，不盲目覆盖。

第三方素材权限和来源范围见[NOTICE](../NOTICE.md)，贡献约定见[CONTRIBUTING](../CONTRIBUTING.md)。本文件说明发布步骤，不自动创建仓库、提交、推送或发布Release。
