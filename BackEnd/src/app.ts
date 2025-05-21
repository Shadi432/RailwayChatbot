import express, { text } from 'express';
import { Builder, Browser, By, until, WebElement, locateWith } from "selenium-webdriver";

const app = express();
const port = 3000;

const LINK_BR_FARES = "https://www.brfares.com/";

const WALK_UP_STANDARD_ID = "tclass-0-1-div"

// Returns a JS object: { "TicketName": {"TicketType: "Return/Single", "Adult": "Price", "Child": "Price"}}
async function getFareInfo(originStation: string, destinationStation: string) {
  let driver: Builder = await new Builder().forBrowser(Browser.CHROME).build();
  const journeyData = {}

  try {
    await driver.manage().setTimeouts({ implicit: 2000 });
    await driver.get(LINK_BR_FARES);

    // Appears over the content the first time you open the site.
    const PersonalDataConsentButton = await driver.findElement(By.css("body > div.fc-consent-root > div.fc-dialog-container > div.fc-dialog.fc-choice-dialog > div.fc-footer-buttons-container > div.fc-footer-buttons > button.fc-button.fc-cta-consent.fc-primary-button"));

    const OriginField: WebElement = await driver.findElement(By.id("origin"));
    const DestinationField: WebElement = await driver.findElement(By.id("destination"));
    const QueryFaresButton: WebElement = await driver.findElement(By.css("#queryparams > table > tbody > tr:nth-child(5) > td > input[type=submit]:nth-child(3)"));

    // Submit Journey Data
    await PersonalDataConsentButton.click();
    await OriginField.sendKeys(originStation);
    await DestinationField.sendKeys(destinationStation);
    await QueryFaresButton.click();

    // Pulling Info from the query results
    const StandardFareTable: WebElement = await driver.findElement(By.id(WALK_UP_STANDARD_ID));
    const FareRowsData: WebElement[] = await StandardFareTable.findElements(By.tagName("tr"));

    for (let i=0; i<FareRowsData.length; i++){
      let textValue = await FareRowsData[i].getText();
      if (textValue.includes("£")) {
        // ANYTIME RETURN, OFF-PEAK R etc
        const ticketName = await FareRowsData[i].findElement(By.tagName("a")).findElement(By.tagName("strong")).getText();

        if (!journeyData[ticketName]){
          const ticketType = getTicketType(ticketName);
          if (!ticketType){
            continue;
          }

          journeyData[ticketName] = {TicketType: ticketType, Adult: "505.50"}
          
          const ticketFor = await FareRowsData[i].findElements(By.className("tiny"));

          for (let adultChild of ticketFor){
            // Gets the parent of an element
            let priceForAgeGroup = await adultChild.findElement(By.xpath("./.."));
            const ticketPricingData: string = await priceForAgeGroup.getText();
            const ticketPricing: string[] = ticketPricingData.split("\n")
            journeyData[ticketName][ticketPricing[0]] = ticketPricing[1];
          }
        }
      }
    }
  } catch (err) {
    console.log(err);
  }

  await driver.quit();

  return journeyData;
}

app.get('/', async (req, res) => {
  const ticketInfo = await getFareInfo(`${req.query.originStation}`, `${req.query.destinationStation}`);
  res.send(ticketInfo);
});

const getTicketType = (ticketName: string)=>{
  const ticketType: string[] = ticketName.split(" ");
  if (ticketType[1].toLowerCase().match("r") ){
    return "Return"
  } else if (ticketType[1].toLowerCase().match("s")){
    return "Single"
  } else {
    return null
  }
}

app.listen(port, () => {
  return console.log(`Express is listening at http://localhost:${port}`);
});
