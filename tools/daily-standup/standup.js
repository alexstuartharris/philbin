#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const readline = require("readline");

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

function ask(question) {
  return new Promise((resolve) => {
    rl.question(question, (answer) => resolve(answer.trim()));
  });
}

function getDateStamp() {
  const now = new Date();
  const yyyy = now.getFullYear();
  const mm = String(now.getMonth() + 1).padStart(2, "0");
  const dd = String(now.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

async function main() {
  const yesterday = await ask("What did you do yesterday? ");
  const today = await ask("What will you do today? ");
  const blockers = await ask("Any blockers? ");
  rl.close();

  const dateStamp = getDateStamp();
  const logsDir = path.join(__dirname, "logs");
  fs.mkdirSync(logsDir, { recursive: true });

  const filePath = path.join(logsDir, `${dateStamp}.md`);
  const content = [
    `# Daily Standup ${dateStamp}`,
    "",
    "## Yesterday",
    yesterday || "-",
    "",
    "## Today",
    today || "-",
    "",
    "## Blockers",
    blockers || "-",
    "",
  ].join("\n");

  fs.writeFileSync(filePath, content, "utf8");
  console.log(`Saved to ${filePath}`);
}

main().catch((err) => {
  rl.close();
  console.error(err);
  process.exit(1);
});
