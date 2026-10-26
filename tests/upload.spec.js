import { test, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
let dir;
test.beforeAll(() => {
  dir = mkdtempSync(join(tmpdir(), 'beauty-clip-'));
  for (const [name, duration] of [['normal',4],['short',0.5]]) execFileSync('ffmpeg',['-v','error','-f','lavfi','-i',`testsrc2=size=180x320:rate=10:duration=${duration}`,'-c:v','libx264','-pix_fmt','yuv420p',join(dir,`${name}.mp4`)]);
});
test.afterAll(() => rmSync(dir,{recursive:true,force:true}));
test('MP4の長さと異なる3枚の画像を表示し、再生できる',async ({page}) => {
  await page.goto('/');
  await page.locator('#file').setInputFiles(join(dir,'normal.mp4'));
  await expect(page.locator('#results')).toBeVisible();
  await expect(page.locator('#duration')).toHaveText('4.00 秒');
  await expect(page.locator('#frames img')).toHaveCount(3);
  const images = await page.locator('#frames img').evaluateAll(els => els.map(i=>i.src));
  expect(new Set(images).size).toBe(3);
  expect(await page.locator('#video').evaluate(async v=>{await v.play(); return !v.paused;})).toBe(true);
  await page.locator('#file').setInputFiles(join(dir,'short.mp4'));
  await expect(page.locator('#duration')).toHaveText('0.50 秒');
  await expect(page.locator('#frames img')).toHaveCount(1);
  await expect(page.locator('#status')).toContainText('3秒未満');
});
test('非MP4と破損したMP4に日本語のエラーを表示する',async ({page}) => {
  await page.goto('/');
  await page.locator('#file').setInputFiles({name:'test.txt',mimeType:'text/plain',buffer:Buffer.from('invalid')});
  await expect(page.getByRole('alert')).toHaveText('MP4形式の動画を選択してください。');
  await page.locator('#file').setInputFiles({name:'broken.mp4',mimeType:'video/mp4',buffer:Buffer.from('invalid')});
  await expect(page.getByRole('alert')).toContainText('この動画を再生できません');
  await expect(page.locator('#results')).toBeHidden();
});
test('モバイル幅で横にはみ出さずに表示する',async ({page})=>{
  await page.setViewportSize({width:375,height:812});await page.goto('/');
  await page.locator('#file').setInputFiles(join(dir,'normal.mp4'));
  await expect(page.locator('#results')).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
