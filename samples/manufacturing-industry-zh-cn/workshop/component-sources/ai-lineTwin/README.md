# 产线三维孪生组件的源码

`../../components/ai-lineTwin/` 是安装时上传的组件包，其中 `index.js` 由这里的 `src/index.js` 打包而来（three.js 一起打进去）。改组件时改 `src/index.js`，再在本目录运行：

```bash
npm install
npm run build
```

打包时去掉了源码里的许可注释，three.js 的许可写在组件包的 `README.md` 末尾，升级 three.js 时一并更新。打包后 `index.js` 的内容变了，组件包的 ID 也会变：安装器按上传后的 ID 写回应用草稿，不用手改 `workshop/apps/line-twin.app.yaml`。
