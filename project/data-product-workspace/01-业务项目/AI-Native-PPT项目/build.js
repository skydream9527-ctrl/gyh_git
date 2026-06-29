const pptxgen = require('pptxgenjs');
const html2pptx = require('/Users/mi/.trae-cn/skills/pptx/scripts/html2pptx');
const path = require('path');

async function build() {
  const pptx = new pptxgen();
  pptx.layout = 'LAYOUT_16x9';
  pptx.author = 'Data Product Team';
  pptx.title = '用 AI 进行生产级工作';

  const slidesDir = path.join(__dirname, 'slides');
  const slideFiles = [
    'slide01-cover.html',
    'slide02-toc.html',
    'slide03-ch1-title.html',
    'slide04-core-argument.html',
    'slide05-industry-data.html',
    'slide06-demo-vs-prod.html',
    'slide07-summary-95.html',
    'slide08-ch2-title.html',
    'slide09-methodology-core.html',
    'slide10-three-phases.html',
    'slide11-question.html',
    'slide12-agent-vs-skill.html',
    'slide13-comparison-table.html',
    'slide14-when-skill.html',
    'slide15-when-agent.html',
    'slide16-ch3-title.html',
    'slide17-dau-trap.html',
    'slide18-alibaba-case.html',
    'slide19-workflow.html',
    'slide20-ai-layers.html',
    'slide21-workflow-mapping.html',
    'slide22-pyramid.html',
    'slide23-seven-stages.html',
    'slide24-demo-easy.html',
    'slide25-ch4-title.html',
    'slide26-mcp.html',
    'slide27-agent-skill.html',
    'slide28-flow-eng.html',
    'slide29-ch5-title.html',
    'slide30-skill-library.html',
    'slide31-case2-compare.html',
    'slide32-compare-table.html',
    'slide33-ch6-title.html',
    'slide34-core-review.html',
    'slide35-roadmap.html',
    'slide36-ending.html',
    'slide37-ideal-vs-reality.html',
    'slide38-quadrant.html',
    'slide39-plan-compare.html',
    'slide40-ideal-plan.html',
    'slide41-core-insights.html',
    'slide42-chat-trap.html',
    'slide43-code-vs-analysis.html',
  ];

  for (let i = 0; i < slideFiles.length; i++) {
    const htmlFile = path.join(slidesDir, slideFiles[i]);
    console.log(`Processing slide ${i + 1}/${slideFiles.length}: ${slideFiles[i]}`);
    try {
      await html2pptx(htmlFile, pptx);
    } catch (e) {
      console.error(`Error on ${slideFiles[i]}: ${e.message}`);
      throw e;
    }
  }

  const outputPath = path.join(__dirname, '..', '用AI进行生产级工作.pptx');
  await pptx.writeFile({ fileName: outputPath });
  console.log(`Presentation saved to: ${outputPath}`);
}

build().catch(e => { console.error(e); process.exit(1); });
