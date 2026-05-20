import { chromium } from "playwright";

async function main() {
  const browser = await chromium.connectOverCDP("http://127.0.0.1:9222");
  const ctx = browser.contexts()[0];
  const pages = ctx.pages();

  const targets = [
    { name: "dr-1 (50人小体量)", id: "32743c6bedc0a5af" },
    { name: "dr-2 (奥克兰华人)", id: "e8c63deef32485b7" },
    { name: "dr-3 (2026新玩法)", id: "bfd3d9a2aa4456ec" },
    { name: "dr-4 (中产ROI)", id: "ba288d9eac3d2c92" },
  ];

  for (const t of targets) {
    const page = pages.find(p => p.url().includes(t.id));
    if (!page) {
      console.log(`❌ ${t.name}: tab not found in CDP`);
      continue;
    }
    const status = await page.evaluate(() => {
      const text = document.body.textContent || "";
      const bodyLen = text.length;
      const hasResult = /Researching \d+ websites?/i.test(text) ||
                        text.includes("正在研究") ||
                        /Browsing \d+/i.test(text);
      const hasFinalReport = text.length > 5000 && (
        text.includes("展示笔记") || text.includes("Show notes") ||
        text.includes("导出") || text.includes("Export") ||
        text.includes("参考资料") || text.includes("Sources")
      );
      const completed = !hasResult && hasFinalReport;
      const stillResearching = hasResult;
      const title = document.title;
      return { bodyLen, hasResult, hasFinalReport, completed, stillResearching, title };
    });
    const stat = status.completed ? "✅ COMPLETED"
              : status.stillResearching ? "⏳ STILL RESEARCHING"
              : "❓ UNKNOWN";
    console.log(`${stat} ${t.name}`);
    console.log(`  title: ${status.title}`);
    console.log(`  bodyLen: ${status.bodyLen}, hasResearching: ${status.hasResult}, hasFinalReport: ${status.hasFinalReport}`);
  }

  await browser.close();
}
main().catch(e => { console.error(e); process.exit(1); });
