import express from 'express';
import { Builder, Browser } from "selenium-webdriver";

const app = express();
const port = 3000;

const LINK_BR_FARES = "https://www.brfares.com/";

async function helloSelenium() {
  let driver: Builder = await new Builder().forBrowser(Browser.CHROME).build();

  await driver.get("https://selenium.dev");

  await driver.quit();
}

app.get('/', (req, res) => {
  helloSelenium();
  res.send('Hello World!');
});

app.listen(port, () => {
  return console.log(`Express is listening at http://localhost:${port}`);
});
