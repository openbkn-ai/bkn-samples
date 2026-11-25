# 产线三维孪生（x-ai.lineTwin）

把一类“设备”对象按工厂 → 工作中心排成三维车间。

- **每行一台设备**。字段角色：`name` 设备名称、`group` 工作中心、`site` 工厂、`kind` 设备类型（决定造型：加工中心、车床、三坐标测量机、测试台、激光打标机，认不出的画成通用机柜）、`status` 设备状态、`running` 加工中的工序数、`queued` 排队的工序数。`name`、`group` 必须，其余缺了照常显示。
- **业务判断不在代码里**：哪个状态算正常由配置 `normalStatus` 给出；加工中、排队数由数据源的关联计数列算出（沿“制造操作的计划机台”关系按工序状态计数）。
- **联动**：点一台设备写入 `selection`（选中对象筛选），页面的详情抽屉随之打开；别处选中的设备在这里高亮。
- three.js 0.187.0 打包在 `index.js` 中（约 150 KB gzip），不从包外加载任何脚本。

## 第三方许可

`index.js` 打包了 three.js 0.187.0，许可如下：

```text
The MIT License

Copyright © 2010-2026 three.js authors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
```
