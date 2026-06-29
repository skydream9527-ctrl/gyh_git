const pptxgen = require('pptxgenjs');
const html2pptx = require('/Users/mi/.trae-cn/skills/pptx/scripts/html2pptx');
const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

const WORKSPACE = '/Users/mi/Desktop/trae-cn/data-product/data-ai-native/测试一下多个skill/ppt_workspace';
const OUTPUT_DIR = '/Users/mi/Desktop/trae-cn/data-product/data-ai-native/测试一下多个skill/ppt_slides';

// Create workspace
if (!fs.existsSync(WORKSPACE)) {
    fs.mkdirSync(WORKSPACE, { recursive: true });
}
if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

// Color palette
const COLORS = {
    primary: '#667eea',
    secondary: '#764ba2',
    accent: '#f093fb',
    dark: '#2d3748',
    light: '#f7fafc',
    success: '#48bb78',
    warning: '#ed8936',
    danger: '#f56565'
};

// Create gradient background
async function createGradientBg(filename, color1, color2, direction = '135deg') {
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="562">
        <defs>
            <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:${color1}"/>
                <stop offset="100%" style="stop-color:${color2}"/>
            </linearGradient>
        </defs>
        <rect width="100%" height="100%" fill="url(#g)"/>
    </svg>`;
    
    await sharp(Buffer.from(svg))
        .png()
        .toFile(path.join(WORKSPACE, filename));
    
    return path.join(WORKSPACE, filename);
}

// Create slides
async function createSlides() {
    // Slide 1: Cover
    const slide1Html = `<!DOCTYPE html>
<html>
<head>
<style>
html { background: #ffffff; }
body {
  width: 720pt; height: 405pt; margin: 0; padding: 0;
  background: #667eea;
  font-family: Arial, sans-serif;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}
h1 {
  color: #ffffff;
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
  color: #ffffff;
  font-size: 16pt;
  margin: 0;
  text-align: center;
}
</style>
</head>
<body>
<h1>版本灰度AB分析报告</h1>
<p class="subtitle">v20.11.1010115 vs v20.11.10115</p>
<p class="info">分析周期：20260116-20260118（3天）</p>
</body>
</html>`;
    fs.writeFileSync(path.join(OUTPUT_DIR, 'slide1.html'), slide1Html);

    // Slide 2: Core Conclusions (Fixed layout)
    const slide2Html = `<!DOCTYPE html>
<html>
<head>
<style>
html { background: #ffffff; }
body {
  width: 720pt; height: 405pt; margin: 0; padding: 0;
  background: #f7fafc;
  font-family: Arial, sans-serif;
  display: flex;
  flex-direction: column;
}
.header {
  background: #667eea;
  padding: 15pt 40pt;
}
.header h1 {
  color: #ffffff;
  font-size: 28pt;
  margin: 0;
}
.content {
  padding: 20pt 40pt 30pt 40pt;
  flex: 1;
}
.section {
  margin-bottom: 15pt;
}
.section h2 {
  color: #2d3748;
  font-size: 16pt;
  margin: 0 0 8pt 0;
}
.highlight {
  background: #ffffff;
  padding: 10pt;
  border-left: 3pt solid #48bb78;
  margin-bottom: 8pt;
}
.highlight p {
  color: #2d3748;
  font-size: 12pt;
  margin: 0;
}
.warning {
  background: #ffffff;
  padding: 10pt;
  border-left: 3pt solid #ed8936;
}
.warning p {
  color: #2d3748;
  font-size: 12pt;
  margin: 0;
}
</style>
</head>
<body>
<div class="header">
  <h1>📊 核心结论</h1>
</div>
<div class="content">
  <div class="section">
    <h2>✅ 整体表现优异</h2>
    <div class="highlight">
      <p><b>用户规模提升：</b>DAU平均提升 <b>6.4%</b></p>
    </div>
    <div class="highlight">
      <p><b>使用时长增加：</b>人均时长提升 <b>1.5%-2.9%</b></p>
    </div>
    <div class="highlight">
      <p><b>消费深度增强：</b>人均VV提升 <b>2.6%-3.7%</b></p>
    </div>
  </div>
  <div class="section">
    <h2>⚠️ 需要关注</h2>
    <div class="warning">
      <p><b>广告CTR略有下降：</b>下降 <b>1.8%-4.7%</b></p>
    </div>
  </div>
</div>
</body>
</html>`;
    fs.writeFileSync(path.join(OUTPUT_DIR, 'slide2.html'), slide2Html);

    // Slide 3: Experiment Overview
    const slide3Html = `<!DOCTYPE html>
<html>
<head>
<style>
html { background: #ffffff; }
body {
  width: 720pt; height: 405pt; margin: 0; padding: 0;
  background: #f7fafc;
  font-family: Arial, sans-serif;
  display: flex;
  flex-direction: column;
}
.header {
  background: #667eea;
  padding: 15pt 40pt;
}
.header h1 {
  color: #ffffff;
  font-size: 28pt;
  margin: 0;
}
.content {
  padding: 20pt 40pt 30pt 40pt;
  flex: 1;
}
.info-box {
  background: #ffffff;
  padding: 15pt;
  margin-bottom: 15pt;
  border-radius: 8pt;
}
.info-box h2 {
  color: #2d3748;
  font-size: 16pt;
  margin: 0 0 8pt 0;
}
.info-box p {
  color: #4a5568;
  font-size: 13pt;
  margin: 4pt 0;
}
</style>
</head>
<body>
<div class="header">
  <h1>📋 实验概览</h1>
</div>
<div class="content">
  <div class="info-box">
    <h2>基本信息</h2>
    <p><b>实验组版本：</b>20.11.1010115</p>
    <p><b>对照组版本：</b>20.11.10115</p>
    <p><b>分析时间：</b>20260116-20260118（共3天）</p>
    <p><b>显著性水平：</b>α = 0.05</p>
  </div>
  <div class="info-box">
    <h2>数据完整性</h2>
    <p><b>成功获取：</b>5个模块（大盘、消费、留存、广告、DAU率）</p>
    <p><b>缺失数据：</b>3个模块（埋点监控、规模体验、商业平台）</p>
  </div>
</div>
</body>
</html>`;
    fs.writeFileSync(path.join(OUTPUT_DIR, 'slide3.html'), slide3Html);

    // Slide 4: Key Metrics Comparison
    const slide4Html = `<!DOCTYPE html>
<html>
<head>
<style>
html { background: #ffffff; }
body {
  width: 720pt; height: 405pt; margin: 0; padding: 0;
  background: #f7fafc;
  font-family: Arial, sans-serif;
  display: flex;
  flex-direction: column;
}
.header {
  background: #667eea;
  padding: 15pt 40pt;
}
.header h1 {
  color: #ffffff;
  font-size: 28pt;
  margin: 0;
}
.content {
  padding: 20pt 40pt 30pt 40pt;
  flex: 1;
}
.table-container {
  background: #ffffff;
  padding: 15pt;
  border-radius: 8pt;
}
table {
  width: 100%;
  border-collapse: collapse;
}
th {
  background: #667eea;
  color: #ffffff;
  padding: 10pt;
  text-align: left;
  font-size: 13pt;
}
td {
  padding: 10pt;
  border-bottom: 1pt solid #e2e8f0;
  font-size: 13pt;
}
.positive {
  color: #48bb78;
  font-weight: bold;
}
</style>
</head>
<body>
<div class="header">
  <h1>📈 核心指标对比（大盘用户）</h1>
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
    fs.writeFileSync(path.join(OUTPUT_DIR, 'slide4.html'), slide4Html);

    // Slide 5: User Duration Analysis
    const slide5Html = `<!DOCTYPE html>
<html>
<head>
<style>
html { background: #ffffff; }
body {
  width: 720pt; height: 405pt; margin: 0; padding: 0;
  background: #f7fafc;
  font-family: Arial, sans-serif;
  display: flex;
  flex-direction: column;
}
.header {
  background: #667eea;
  padding: 15pt 40pt;
}
.header h1 {
  color: #ffffff;
  font-size: 28pt;
  margin: 0;
}
.content {
  padding: 20pt 40pt 30pt 40pt;
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
  background: #ffffff;
  padding: 12pt;
  margin-bottom: 12pt;
  border-radius: 8pt;
  border-left: 3pt solid #48bb78;
}
.finding-box h3 {
  color: #2d3748;
  font-size: 14pt;
  margin: 0 0 6pt 0;
}
.finding-box p {
  color: #4a5568;
  font-size: 12pt;
  margin: 0;
}
.chart-placeholder {
  background: #e2e8f0;
  width: 100%;
  height: 220pt;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8pt;
}
</style>
</head>
<body>
<div class="header">
  <h1>⏱️ 大盘指标分析</h1>
</div>
<div class="content">
  <div class="left">
    <div class="finding-box">
      <h3>核心发现</h3>
      <p>实验组人均使用时长整体高于对照组</p>
    </div>
    <div class="finding-box">
      <h3>老用户表现</h3>
      <p>稳定提升 1.5%-2.9%</p>
    </div>
    <div class="finding-box">
      <h3>新用户表现</h3>
      <p>第2天提升显著 +26%</p>
    </div>
  </div>
  <div class="right">
    <div id="chart" class="placeholder chart-placeholder" style="width: 300pt; height: 220pt;"></div>
  </div>
</div>
</body>
</html>`;
    fs.writeFileSync(path.join(OUTPUT_DIR, 'slide5.html'), slide5Html);

    // Slide 6: Retention Analysis
    const slide6Html = `<!DOCTYPE html>
<html>
<head>
<style>
html { background: #ffffff; }
body {
  width: 720pt; height: 405pt; margin: 0; padding: 0;
  background: #f7fafc;
  font-family: Arial, sans-serif;
  display: flex;
  flex-direction: column;
}
.header {
  background: #667eea;
  padding: 15pt 40pt;
}
.header h1 {
  color: #ffffff;
  font-size: 28pt;
  margin: 0;
}
.content {
  padding: 20pt 40pt 30pt 40pt;
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
.highlight-box {
  background: #ffffff;
  padding: 15pt;
  margin-bottom: 12pt;
  border-radius: 8pt;
  border-left: 3pt solid #48bb78;
}
.highlight-box h3 {
  color: #2d3748;
  font-size: 14pt;
  margin: 0 0 8pt 0;
}
.highlight-box p {
  color: #4a5568;
  font-size: 12pt;
  margin: 3pt 0;
}
.big-number {
  color: #48bb78;
  font-size: 32pt;
  font-weight: bold;
}
.chart-placeholder {
  background: #e2e8f0;
  width: 100%;
  height: 220pt;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8pt;
}
</style>
</head>
<body>
<div class="header">
  <h1>🔄 留存指标分析</h1>
</div>
<div class="content">
  <div class="left">
    <div class="highlight-box">
      <h3>新用户留存率显著提升</h3>
      <p>最高提升幅度：</p>
      <p class="big-number">+20%</p>
    </div>
    <div class="highlight-box">
      <h3>大盘用户</h3>
      <p>留存率基本持平</p>
    </div>
    <div class="highlight-box">
      <h3>老用户</h3>
      <p>留存率稳定</p>
    </div>
  </div>
  <div class="right">
    <div id="chart" class="placeholder chart-placeholder" style="width: 300pt; height: 220pt;"></div>
  </div>
</div>
</body>
</html>`;
    fs.writeFileSync(path.join(OUTPUT_DIR, 'slide6.html'), slide6Html);

    // Slide 7: Recommendations
    const slide7Html = `<!DOCTYPE html>
<html>
<head>
<style>
html { background: #ffffff; }
body {
  width: 720pt; height: 405pt; margin: 0; padding: 0;
  background: #f7fafc;
  font-family: Arial, sans-serif;
  display: flex;
  flex-direction: column;
}
.header {
  background: #667eea;
  padding: 15pt 40pt;
}
.header h1 {
  color: #ffffff;
  font-size: 28pt;
  margin: 0;
}
.content {
  padding: 15pt 40pt 30pt 40pt;
  flex: 1;
  display: flex;
}
.section {
  background: #ffffff;
  padding: 12pt;
  margin-right: 12pt;
  border-radius: 8pt;
  flex: 1;
}
.section:last-child {
  margin-right: 0;
}
.section h2 {
  color: #2d3748;
  font-size: 14pt;
  margin: 0 0 6pt 0;
}
.section ul {
  margin: 0;
  padding-left: 15pt;
}
.section li {
  color: #4a5568;
  font-size: 11pt;
  margin-bottom: 4pt;
}
</style>
</head>
<body>
<div class="header">
  <h1>💡 综合建议</h1>
</div>
<div class="content">
  <div class="section">
    <h2>✅ 优势保持</h2>
    <ul>
      <li>观察DAU增长</li>
      <li>分析留存提升</li>
      <li>保持VV增长</li>
    </ul>
  </div>
  <div class="section">
    <h2>⚠️ 问题优化</h2>
    <ul>
      <li>排查广告CTR下降</li>
      <li>优化新用户引导</li>
      <li>补充缺失数据</li>
    </ul>
  </div>
  <div class="section">
    <h2>🔍 后续行动</h2>
    <ul>
      <li>延长观察期</li>
      <li>显著性检验</li>
      <li>深入分析群体</li>
    </ul>
  </div>
</div>
</body>
</html>`;
    fs.writeFileSync(path.join(OUTPUT_DIR, 'slide7.html'), slide7Html);

    console.log('✅ All HTML slides created');
}

// Main function
async function main() {
    try {
        console.log('Creating HTML slides...');
        await createSlides();
        
        console.log('\nConverting to PowerPoint...');
        const pptx = new pptxgen();
        pptx.layout = 'LAYOUT_16x9';
        pptx.author = 'AB Test Analysis';
        pptx.title = '版本灰度AB分析报告';
        
        // Convert each slide
        const slideFiles = [
            'slide1.html',
            'slide2.html',
            'slide3.html',
            'slide4.html',
            'slide5.html',
            'slide6.html',
            'slide7.html'
        ];
        
        for (const file of slideFiles) {
            console.log(`  Processing ${file}...`);
            const { slide, placeholders } = await html2pptx(
                path.join(OUTPUT_DIR, file),
                pptx
            );
            
            // Add charts to placeholders
            if (placeholders.length > 0) {
                if (file === 'slide5.html') {
                    // Duration comparison chart
                    slide.addChart(pptx.charts.BAR, [{
                        name: '对照组',
                        labels: ['大盘用户', '老用户', '新用户'],
                        values: [13.6, 13.7, 2.7]
                    }, {
                        name: '实验组',
                        labels: ['大盘用户', '老用户', '新用户'],
                        values: [14.1, 14.1, 2.4]
                    }], {
                        ...placeholders[0],
                        barDir: 'col',
                        showTitle: true,
                        title: '人均使用时长对比(分钟)',
                        showLegend: true,
                        legendPos: 'b',
                        chartColors: ['667eea', '48bb78'],
                        showCatAxisTitle: true,
                        catAxisTitle: '用户类型',
                        showValAxisTitle: true,
                        valAxisTitle: '时长(分钟)'
                    });
                } else if (file === 'slide6.html') {
                    // Retention chart
                    slide.addChart(pptx.charts.LINE, [{
                        name: '对照组',
                        labels: ['0116', '0117', '0118'],
                        values: [30.3, 27.0, 24.2]
                    }, {
                        name: '实验组',
                        labels: ['0116', '0117', '0118'],
                        values: [28.4, 29.4, 29.0]
                    }], {
                        ...placeholders[0],
                        showTitle: true,
                        title: '新用户留存率趋势(%)',
                        showLegend: true,
                        legendPos: 'b',
                        chartColors: ['667eea', '48bb78'],
                        lineSize: 3,
                        showCatAxisTitle: true,
                        catAxisTitle: '日期',
                        showValAxisTitle: true,
                        valAxisTitle: '留存率(%)'
                    });
                }
            }
        }
        
        // Save presentation
        const outputFile = './版本灰度AB分析报告.pptx';
        await pptx.writeFile({ fileName: outputFile });
        console.log(`\n✅ Presentation saved to: ${outputFile}`);
        
    } catch (error) {
        console.error('Error:', error);
        process.exit(1);
    }
}

main();
