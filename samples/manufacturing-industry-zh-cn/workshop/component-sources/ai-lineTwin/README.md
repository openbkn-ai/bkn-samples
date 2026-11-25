# 产线三维孪生组件的源码

组件包 `../../components/ai-lineTwin/` 里的 `index.js` 不进仓库，由这里的 `src/index.js` 打包而来（three.js 一起打进去）。构建样例候选包时，`tools/publication/build_candidate.py` 把本目录拷到临时目录，按 `package-lock.json` 安装锁定的依赖（`npm ci --ignore-scripts`），运行 `npm run build`，把 `dist/` 里的文件放进组件包。所以构建候选包的机器需要 Node.js 与 npm。

改组件时改 `src/index.js`。本地看效果可以在本目录运行：

```bash
npm ci
npm run build
```

再把 `dist/index.js` 拷到组件包目录试装，试完删掉，不要提交。升级依赖时改 `package.json` 里的固定版本，运行 `npm install` 更新 `package-lock.json`，两个文件一起提交。

打包时去掉了源码里的许可注释，three.js 的许可写在组件包的 `README.md` 末尾，升级 three.js 时一并更新。

应用文件 `workshop/apps/line-twin.app.yaml` 的 `components` 只写组件类型，不写组件包 ID：上传后 Workshop 给出 ID，安装器把它写进草稿再发布。
