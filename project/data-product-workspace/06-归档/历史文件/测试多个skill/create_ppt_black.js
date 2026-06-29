const pptxgen = require('pptxgenjs');
const html2pptx = require('/Users/mi/.trae-cn/skills/pptx/scripts/html2pptx');
const fs = require('fs');
const path = require('path');

const OUTPUT_DIR = '/Users/mi/Desktop/trae-cn/data-product/data-ai-native/测试一下多个skill/ppt_slides_black';

// Create output directory
if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

// Dark theme colors
const COLORS = {
    bg: '#1a1a1a',
    bgLight: '#2d2d2d',
    primary: '#00d4ff',
    secondary: '#7c3aed',
    accent: '#f59e0b',
    text: '#ffffff',
    textLight: '#a0a0a0',
    success: '#10b981',
    warning: '#f59e0b',
    danger: '#ef4444'
};

// Create slides
function createSlides() {
    // Slide 1: Cover
    const slide1Html = `<!DOCTYPE html>
<html>
<head>
<style>
html { background: #ffffff; }
body {
  width: 720pt; height: 405pt; margin: 0; padding: 0;
  background: #1a1a1a;
  font-family: Arial, sans-serif;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}
h1 {
  color: #00d4ff;
  font-size: 48pt;
  margin: 0 0 20pt 0;
  text-align: center;
}
.subtitle {
  color: #ffffff;
  font-size: 24pt;
  margin: 0 0 30pt 0;
  text-align: center;
}
.info {
  color: #a0a0a0;
  font-size: 16pt;
  margin: 0;
  text-align: center;
}
</style>
</head>
<body>
<h1>版本灰度AB分析执行记录</h1>
<p class="subtitle">v20.11.1010115 vs v20.11.10115</p>
<p class="info">报告生成时间：2026年4月10日</p>
</body>
</html>`;
    fs.writeFileSync(path.join(OUTPUT_DIR, 'slide1.html'), slide1Html);

    // Slide 2: Overview
    const slide2Html = `<!DOCTYPE html>
<html>
<head>
<style>
html { background: #ffffff; }
body {
  width: 720pt; height: 405pt; margin: 0; padding: 0;
  background: #1a1a1a;
  font-family: Arial, sans-serif;
  display: flex;
  flex-direction: column;
}
.header {
  background: #2d2d2d;
  padding: 12pt 40pt;
  border-bottom: 2pt solid #00d4ff;
}
.header h1 {
  color: #00d4ff;
  font-size: 26pt;
  margin: 0;
}
.content {
  padding: 15pt 40pt 30pt 40pt;
  flex: 1;
}
.card {
  background: #2d2d2d;
  padding: 12pt;
  margin-bottom: 10pt;
  border-radius: 8pt;
  border-left: 3pt solid #00d4ff;
}
.card h2 {
  color: #00d4ff;
  font-size: 14pt;
  margin: 0 0 6pt 0;
}
.card p {
  color: #ffffff;
  font-size: 12pt;
  margin: 3pt 0;
}
.highlight {
  color: #10b981;
  font-weight: bold;
}
.warning {
  color: #f59e0b;
  font-weight: bold;
}
</style>
</head>
<body>
<div class="header">
  <h1>📊 执行概览</h1>
</div>
<div class="content">
  <div class="card">
    <h2>任务完成情况</h2>
    <p><span class="highlight">✅ SQL生成：</span>16个SQL文件</p>
    <p><span class="highlight">✅ 数据查询：</span>5个模块成功</p>
    <p><span class="highlight">✅ 分析报告：</span>已生成</p>
  </div>
  <div class="card">
    <h2>关键数据</h2>
    <p><span class="highlight">DAU提升：</span>6.47%</p>
    <p><span class="highlight">留存率：</span>提升最高20%</p>
    <p><span class="warning">⚠️ 数据完整性：</span>5/8模块</p>
  </div>
</div>
</body>
</html>`;
    fs.writeFileSync(path.join(OUTPUT_DIR, 'slide2.html'), slide2Html);

    // Slide 3: Task Background
    const slide3Html = `<!DOCTYPE html>
<html>
<head>
<style>
html { background: #ffffff; }
body {
  width: 720pt; height: 405pt; margin: 0; padding: 0;
  background: #1a1a1a;
  font-family: Arial, sans-serif;
  display: flex;
  flex-direction: column;
}
.header {
  background: #2d2d2d;
  padding: 12pt 40pt;
  border-bottom: 2pt solid #7c3aed;
}
.header h1 {
  color: #7c3aed;
  font-size: 26pt;
  margin: 0;
}
.content {
  padding: 15pt 40pt 30pt 40pt;
  flex: 1;
}
.info-box {
  background: #2d2d2d;
  padding: 12pt;
  margin-bottom: 10pt;
  border-radius: 8pt;
}
.info-box h2 {
  color: #7c3aed;
  font-size: 14pt;
  margin: 0 0 6pt 0;
}
.info-box p {
  color: #ffffff;
  font-size: 12pt;
  margin: 3pt 0;
}
.label {
  color: #a0a0a0;
}
</style>
</head>
<body>
<div class="header">
  <h1>📋 任务背景</h1>
</div>
<div class="content">
  <div class="info-box">
    <h2>版本信息</h2>
    <p><span class="label">实验组版本：</span>20.11.1010115</p>
    <p><span class="label">对照组版本：</span>20.11.10115</p>
    <p><span class="label">分析周期：</span>20260116-20260118</p>
  </div>
  <div class="info-box">
    <h2>任务目标</h2>
    <p>1. 生成SQL文件</p>
    <p>2. 执行数据查询</p>
    <p>3. 生成分析报告</p>
    <p>4. 创建飞书文档</p>
  </div>
</div>
</body>
</html>`;
    fs.writeFileSync(path.join(OUTPUT_DIR, 'slide3.html'), slide3Html);

    // Slide 4: Execution Process
    const slide4Html = `<!DOCTYPE html>
<html>
<head>
<style>
html { background: #ffffff; }
body {
  width: 720pt; height: 405pt; margin: 0; padding: 0;
  background: #1a1a1a;
  font-family: Arial, sans-serif;
  display: flex;
  flex-direction: column;
}
.header {
  background: #2d2d2d;
  padding: 15pt 40pt;
  border-bottom: 2pt solid #f59e0b;
}
.header h1 {
  color: #f59e0b;
  font-size: 28pt;
  margin: 0;
}
.content {
  padding: 15pt 40pt 30pt 40pt;
  flex: 1;
}
.step {
  background: #2d2d2d;
  padding: 12pt;
  margin-bottom: 10pt;
  border-radius: 8pt;
  border-left: 3pt solid #10b981;
}
.step h3 {
  color: #00d4ff;
  font-size: 14pt;
  margin: 0 0 6pt 0;
}
.step p {
  color: #ffffff;
  font-size: 12pt;
  margin: 3pt 0;
}
.status-ok {
  color: #10b981;
  font-weight: bold;
}
.status-warn {
  color: #f59e0b;
  font-weight: bold;
}
</style>
</head>
<body>
<div class="header">
  <h1>⚙️ 执行过程</h1>
</div>
<div class="content">
  <div class="step">
    <h3>步骤1：SQL生成</h3>
    <p><span class="status-ok">✅ 完成</span> - 生成16个SQL文件（8个指标查询 + 8个置信度计算）</p>
  </div>
  <div class="step">
    <h3>步骤2：数据查询</h3>
    <p><span class="status-warn">⚠️ 部分成功</span> - 5/8模块数据获取成功</p>
    <p>成功：大盘、消费、留存、广告、DAU率</p>
    <p>失败：埋点监控、规模体验、商业平台</p>
  </div>
  <div class="step">
    <h3>步骤3：分析报告</h3>
    <p><span class="status-ok">✅ 完成</span> - 生成完整分析报告并写入飞书文档</p>
  </div>
</div>
</body>
</html>`;
    fs.writeFileSync(path.join(OUTPUT_DIR, 'slide4.html'), slide4Html);

    // Slide 5: Analysis Results
    const slide5Html = `<!DOCTYPE html>
<html>
<head>
<style>
html { background: #ffffff; }
body {
  width: 720pt; height: 405pt; margin: 0; padding: 0;
  background: #1a1a1a;
  font-family: Arial, sans-serif;
  display: flex;
  flex-direction: column;
}
.header {
  background: #2d2d2d;
  padding: 15pt 40pt;
  border-bottom: 2pt solid #10b981;
}
.header h1 {
  color: #10b981;
  font-size: 28pt;
  margin: 0;
}
.content {
  padding: 20pt 40pt 30pt 40pt;
  flex: 1;
}
.table-container {
  background: #2d2d2d;
  padding: 15pt;
  border-radius: 8pt;
}
table {
  width: 100%;
  border-collapse: collapse;
}
th {
  background: #3d3d3d;
  color: #00d4ff;
  padding: 10pt;
  text-align: left;
  font-size: 13pt;
}
td {
  padding: 10pt;
  border-bottom: 1pt solid #3d3d3d;
  font-size: 13pt;
  color: #ffffff;
}
.positive {
  color: #10b981;
  font-weight: bold;
}
</style>
</head>
<body>
<div class="header">
  <h1>📈 分析结果（核心指标）</h1>
</div>
<div class="content">
  <div class="table-container">
    <table>
      <tr>
        <th>指标</th>
        <th>对照组</th>
        <th>实验组</th>
        <th>提升幅度</th>
      </tr>
      <tr>
        <td>DAU</td>
        <td>206,619</td>
        <td>219,990</td>
        <td class="positive">+6.47%</td>
      </tr>
      <tr>
        <td>人均曝光</td>
        <td>11.70</td>
        <td>11.81</td>
        <td class="positive">+0.90%</td>
      </tr>
      <tr>
        <td>人均VV</td>
        <td>3.65</td>
        <td>3.77</td>
        <td class="positive">+3.10%</td>
      </tr>
      <tr>
        <td>CTR</td>
        <td>31.04%</td>
        <td>31.70%</td>
        <td class="positive">+2.10%</td>
      </tr>
    </table>
  </div>
</div>
</body>
</html>`;
    fs.writeFileSync(path.join(OUTPUT_DIR, 'slide5.html'), slide5Html);

    // Slide 6: Key Findings
    const slide6Html = `<!DOCTYPE html>
<html>
<head>
<style>
html { background: #ffffff; }
body {
  width: 720pt; height: 405pt; margin: 0; padding: 0;
  background: #1a1a1a;
  font-family: Arial, sans-serif;
  display: flex;
  flex-direction: column;
}
.header {
  background: #2d2d2d;
  padding: 12pt 40pt;
  border-bottom: 2pt solid #00d4ff;
}
.header h1 {
  color: #00d4ff;
  font-size: 26pt;
  margin: 0;
}
.content {
  padding: 15pt 40pt 30pt 40pt;
  flex: 1;
  display: flex;
}
.left {
  flex: 1;
  padding-right: 15pt;
}
.right {
  flex: 1;
}
.finding-box {
  background: #2d2d2d;
  padding: 10pt;
  margin-bottom: 10pt;
  border-radius: 8pt;
  border-left: 3pt solid #10b981;
}
.finding-box h3 {
  color: #10b981;
  font-size: 13pt;
  margin: 0 0 5pt 0;
}
.finding-box p {
  color: #ffffff;
  font-size: 11pt;
  margin: 0;
}
.chart-placeholder {
  background: #2d2d2d;
  width: 100%;
  height: 200pt;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8pt;
}
</style>
</head>
<body>
<div class="header">
  <h1>🔍 关键发现</h1>
</div>
<div class="content">
  <div class="left">
    <div class="finding-box">
      <h3>用户规模提升</h3>
      <p>DAU平均提升 6.47%</p>
    </div>
    <div class="finding-box">
      <h3>使用时长增加</h3>
      <p>人均时长提升 1.5%-2.9%</p>
    </div>
    <div class="finding-box">
      <h3>消费深度增强</h3>
      <p>人均VV提升 2.6%-3.7%</p>
    </div>
    <div class="finding-box">
      <h3>新用户表现突出</h3>
      <p>留存率提升最高达 20%</p>
    </div>
  </div>
  <div class="right">
    <div id="chart" class="placeholder chart-placeholder" style="width: 280pt; height: 200pt;"></div>
  </div>
</div>
</body>
</html>`;
    fs.writeFileSync(path.join(OUTPUT_DIR, 'slide6.html'), slide6Html);

    // Slide 7: Issues and Solutions
    const slide7Html = `<!DOCTYPE html>
<html>
<head>
<style>
html { background: #ffffff; }
body {
  width: 720pt; height: 405pt; margin: 0; padding: 0;
  background: #1a1a1a;
  font-family: Arial, sans-serif;
  display: flex;
  flex-direction: column;
}
.header {
  background: #2d2d2d;
  padding: 15pt 40pt;
  border-bottom: 2pt solid #ef4444;
}
.header h1 {
  color: #ef4444;
  font-size: 28pt;
  margin: 0;
}
.content {
  padding: 15pt 40pt 30pt 40pt;
  flex: 1;
  display: flex;
}
.section {
  background: #2d2d2d;
  padding: 12pt;
  margin-right: 12pt;
  border-radius: 8pt;
  flex: 1;
}
.section:last-child {
  margin-right: 0;
}
.section h2 {
  color: #f59e0b;
  font-size: 14pt;
  margin: 0 0 6pt 0;
}
.section ul {
  margin: 0;
  padding-left: 15pt;
}
.section li {
  color: #ffffff;
  font-size: 11pt;
  margin-bottom: 4pt;
}
</style>
</head>
<body>
<div class="header">
  <h1>⚠️ 问题与优化</h1>
</div>
<div class="content">
  <div class="section">
    <h2>遇到的问题</h2>
    <ul>
      <li>SQL语法错误</li>
      <li>认证失败</li>
      <li>数据权限不足</li>
      <li>部分模块缺失</li>
    </ul>
  </div>
  <div class="section">
    <h2>解决方案</h2>
    <ul>
      <li>修复SQL语法</li>
      <li>配置认证token</li>
      <li>申请数据权限</li>
      <li>使用可用数据</li>
    </ul>
  </div>
  <div class="section">
    <h2>优化方向</h2>
    <ul>
      <li>提升数据完整性</li>
      <li>增强分析深度</li>
      <li>提高自动化程度</li>
      <li>优化文档质量</li>
    </ul>
  </div>
</div>
</body>
</html>`;
    fs.writeFileSync(path.join(OUTPUT_DIR, 'slide7.html'), slide7Html);

    // Slide 8: Summary
    const slide8Html = `<!DOCTYPE html>
<html>
<head>
<style>
html { background: #ffffff; }
body {
  width: 720pt; height: 405pt; margin: 0; padding: 0;
  background: #1a1a1a;
  font-family: Arial, sans-serif;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}
h1 {
  color: #00d4ff;
  font-size: 36pt;
  margin: 0 0 30pt 0;
  text-align: center;
}
.summary-box {
  background: #2d2d2d;
  padding: 20pt 40pt;
  border-radius: 8pt;
  border: 2pt solid #00d4ff;
  margin-bottom: 20pt;
}
.summary-box p {
  color: #ffffff;
  font-size: 16pt;
  margin: 8pt 0;
  text-align: center;
}
.highlight {
  color: #10b981;
  font-weight: bold;
}
.footer {
  color: #a0a0a0;
  font-size: 12pt;
  margin-top: 30pt;
}
</style>
</head>
<body>
<h1>✅ 任务完成总结</h1>
<div class="summary-box">
  <p><span class="highlight">SQL生成：</span>16个文件</p>
  <p><span class="highlight">数据查询：</span>5个模块成功</p>
  <p><span class="highlight">分析报告：</span>已生成</p>
  <p><span class="highlight">飞书文档：</span>已创建</p>
</div>
<p class="footer">报告版本：V3.0 | 生成时间：2026年4月10日</p>
</body>
</html>`;
    fs.writeFileSync(path.join(OUTPUT_DIR, 'slide8.html'), slide8Html);

    console.log('✅ All HTML slides created with dark theme');
}

// Main function
async function main() {
    try {
        console.log('Creating HTML slides with dark theme...');
        createSlides();
        
        console.log('\nConverting to PowerPoint...');
        const pptx = new pptxgen();
        pptx.layout = 'LAYOUT_16x9';
        pptx.author = 'AB Test Analysis';
        pptx.title = '版本灰度AB分析执行记录';
        
        // Convert each slide
        const slideFiles = [
            'slide1.html',
            'slide2.html',
            'slide3.html',
            'slide4.html',
            'slide5.html',
            'slide6.html',
            'slide7.html',
            'slide8.html'
        ];
        
        for (const file of slideFiles) {
            console.log(`  Processing ${file}...`);
            const { slide, placeholders } = await html2pptx(
                path.join(OUTPUT_DIR, file),
                pptx
            );
            
            // Add charts to placeholders
            if (placeholders.length > 0 && file === 'slide6.html') {
                // DAU comparison chart
                slide.addChart(pptx.charts.BAR, [{
                    name: '对照组',
                    labels: ['DAU', '人均VV', 'CTR'],
                    values: [206619, 3.65, 31.04]
                }, {
                    name: '实验组',
                    labels: ['DAU', '人均VV', 'CTR'],
                    values: [219990, 3.77, 31.70]
                }], {
                    ...placeholders[0],
                    barDir: 'col',
                    showTitle: true,
                    title: '核心指标对比',
                    showLegend: true,
                    legendPos: 'b',
                    chartColors: ['00d4ff', '10b981'],
                    showCatAxisTitle: true,
                    catAxisTitle: '指标',
                    showValAxisTitle: true,
                    valAxisTitle: '数值'
                });
            }
        }
        
        // Save presentation
        const outputFile = '/Users/mi/Desktop/trae-cn/data-product/data-ai-native/测试一下多个skill/版本灰度AB分析执行记录_黑色主题.pptx';
        await pptx.writeFile({ fileName: outputFile });
        console.log(`\n✅ Presentation saved to: ${outputFile}`);
        
    } catch (error) {
        console.error('Error:', error);
        process.exit(1);
    }
}

main();
