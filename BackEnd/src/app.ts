import express, { text } from 'express';
import { Builder, Browser, By, until, WebElement, locateWith } from "selenium-webdriver";

const app = express();
const port = 3000;

const LINK_BR_FARES = "https://www.brfares.com/";
const TARGET_TICKETS = ["ANYTIME DAY R", "OFF-PEAK R", "ANYTIME DAY S", "OFF-PEAK S"]

const WALK_UP_STANDARD_ID = "tclass-0-1-div"

// Returns a JS object: { "TicketType": {"Adult": "Price", "Child": "Price"}}
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

      if (textValue.includes("RETURN FARES") || textValue.includes("SINGLE FARES")) {
        // This is based of the knowledge that the HTML is parsed from top down.
        if (i != FareRowsData.length-1){
          // The +5 is just a quirk with how I need to get the next row since there are intermediate trs for showing ticket instructions/info.
          for (let j=1; j<6; j+=4){
            // ADULT/CHILD
            const ticketFor = await FareRowsData[i+j].findElements(By.className("tiny"));
            // ANYTIME RETURN, OFF-PEAK R etc
            const ticketTypeData: string = await FareRowsData[i+j].findElement(By.tagName("td")).getText()
            const ticketType: string = ticketTypeData.split("\n")[0];
            // Ticket type this is used to index the array and then have a dictionary with "Adult and Child" for each ticket type

            journeyData[ticketType] = {};
            for (let adultChild of ticketFor){
              // Gets the parent of an element
              let priceForAgeGroup = await adultChild.findElement(By.xpath("./.."));
              const ticketPricingData: string = await priceForAgeGroup.getText();
              const ticketPricing: string[] = ticketPricingData.split("\n")
              journeyData[ticketType][ticketPricing[0]] = ticketPricing[1];
            }
          }
        }
      }
    }
  } catch (err) {
    console.log(err);
  }

  console.log(`Finished: `);
  console.log(journeyData);

  await driver.quit();

  return journeyData;
}

app.get('/', (req, res) => {
  const ticketInfo = getFareInfo("NRW", "LST");
  res.send('Hello World!');
});

app.listen(port, () => {
  return console.log(`Express is listening at http://localhost:${port}`);
});
