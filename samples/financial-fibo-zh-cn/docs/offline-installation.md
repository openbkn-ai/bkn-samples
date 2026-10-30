# 离线候选包安装

要求 **OpenBKN >=0.2.1 <0.3.0**，并支持 `sample offline.v2` 与 `database.shared`。

1. 在仓库根目录执行 `python3 -m tools.publication.build_candidate samples/SAMPLE --version VERSION --output /absolute/output --shared-database`。Git 暂存区明确限定交付文件，包内容取工作区文件；本地验收不需要提交、推送或更新目录清单。
2. 在 Studio 将生成的 `package.tar.gz` 导入为离线样例。对应接口为 `POST /api/studio/samples/import`，通过已有本地授权会话提交原始 gzip 字节。
3. 在样例卡片安装导入版本。安装器创建受所有权回执管理的共享 MariaDB 数据库，发现20张表、导入BKN并绑定20类对象；同时安装并核验3个原生只读函数及2个Skill。安装还逐字段核对78,356条记录、模型数量、绑定和全部对象类的实际查询。
4. 必须等待5个阶段全部成功；部分安装不算验收。卸载通过样例卡片的标准卸载操作，按所有权回执清理资源，不手工删除共享数据库或其他知识网络。
5. 用[业务场景测试集 v1](../bkn-eval/baselines/2026-10-30-business-scenarios-v1/README.md)让未读答案的智能体通过 MCP 每题跑一轮；模型只接收题目和已安装能力，保存回答后才用参考答案评分，保留失败和工具/会话错误。

两个语言是独立样例，具有独立数据库、知识网络和安装回执。当前候选不加入线上发布目录。隔离盲测、扰动答案、原始模型记录和评分保存在独立验收目录，不混入数据源或安装包。SQL回放与原生函数比对分别证明冻结查询和部署一致性，不能代替模型业务准确率。
