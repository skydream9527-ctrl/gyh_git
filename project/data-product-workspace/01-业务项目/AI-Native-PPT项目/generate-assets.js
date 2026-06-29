const sharp = require('sharp');
const path = require('path');

async function createGradientBg(filename, color1, color2, direction = 'diagonal') {
  let x1, y1, x2, y2;
  if (direction === 'diagonal') { x1='0%'; y1='0%'; x2='100%'; y2='100%'; }
  else if (direction === 'horizontal') { x1='0%'; y1='0%'; x2='100%'; y2='0%'; }
  else { x1='0%'; y1='0%'; x2='0%'; y2='100%'; }

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="810">
    <defs><linearGradient id="g" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}">
      <stop offset="0%" style="stop-color:${color1}"/>
      <stop offset="100%" style="stop-color:${color2}"/>
    </linearGradient></defs>
    <rect width="100%" height="100%" fill="url(#g)"/>
  </svg>`;
  await sharp(Buffer.from(svg)).png().toFile(path.join(__dirname, 'slides', filename));
}

async function createAccentBar(filename, color, width, height) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}">
    <rect width="100%" height="100%" fill="${color}" rx="4"/>
  </svg>`;
  await sharp(Buffer.from(svg)).png().toFile(path.join(__dirname, 'slides', filename));
}

async function createCircle(filename, color, size) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}">
    <circle cx="${size/2}" cy="${size/2}" r="${size/2}" fill="${color}" opacity="0.15"/>
  </svg>`;
  await sharp(Buffer.from(svg)).png().toFile(path.join(__dirname, 'slides', filename));
}

async function main() {
  await createGradientBg('bg-cover.png', '#0D1117', '#161B22');
  await createGradientBg('bg-dark.png', '#0D1117', '#0D1117');
  await createGradientBg('bg-section.png', '#0D1117', '#1A2332', 'diagonal');
  await createGradientBg('bg-accent.png', '#0D1117', '#112240', 'vertical');
  await createAccentBar('bar-blue.png', '#58A6FF', 200, 8);
  await createAccentBar('bar-orange.png', '#F0883E', 200, 8);
  await createAccentBar('bar-cyan.png', '#79C0FF', 200, 8);
  await createCircle('circle-blue.png', '#58A6FF', 400);
  await createCircle('circle-orange.png', '#F0883E', 300);
  console.log('Assets generated!');
}

main().catch(console.error);
