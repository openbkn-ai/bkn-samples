# 产线三维孪生组件的源码

`../../components/ai-lineTwin/` 是安装时上传的组件包，其中 `index.js` 由这里的 `src/index.js` 打包而来（three.js 一起打进去）。改组件时改 `src/index.js`，再在本目录运行：

```bash
npm install
npm run build
```

打包时去掉了源码里的许可注释，three.js 的许可写在组件包的 `README.md` 末尾，升级 three.js 时一并更新。

组件包里任何文件变了，组件包的 ID 都会变。同时把 `workshop/apps/line-twin.app.yaml` 里 `components` 的 `package` 改成新 ID：运行 `python -m unittest installer.tests.test_workshop_apps`，`test_the_repository_apps_draw_only_with_packages_their_sample_brings` 会报出应写的 ID。漏改时安装器仍能装好（它按上传后 Workshop 给的 ID 保存草稿再发布），但仓库里的应用文件就和组件包对不上了。
