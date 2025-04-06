# Railway Chatbot Project
This project runs on a NodeJS backend and a React Front-end, both are using typescript.

## Set Up
After cloning the repository, initialise the front-end and back-end by going into the respective directories and using the command `npm install` this will install all the project dependencies.

I'm using Python version 3.12.3, if the code doesn't work with your python version make sure to tell the team.
Also you need to install these python libraries through pip:

### Environment Variables
A .env file will need to be made in the root directory of the BackEnd and it'll need to have the following variables from a [NRDP](https://opendata.nationalrail.co.uk/) account.
**Under Darwin FTP Information on the page**
```
    FTP_HOSTNAME=darwin-dist-xxxxxxxx
    FTP_USERNAME=usernamehere
    FTP_PASSWORD=passwordhere
```

### Dependencies

It's recommended to use a python virtualenv so that the modules aren't installed systemwide which could lead to errors. [VEnv Post](https://stackoverflow.com/questions/41972261/what-is-a-virtualenv-and-why-should-i-use-one)

#### Required Libraries
Dot-Env - For allowing the .env files to work. 
```pip install python-dotenv```


## Instructions for Running the project

To run the front-end or the back-end to test your changes, go to the respective directory then run
`npm run dev`


### Generating the latest Darwin file
If you use the command ```python python BackEnd/src/webscraper.py``` to run the webscraper you'll generate a trainUpdates.dat file which will include the xml records that darwin provides.

# Adding to the project
Make sure to put all new features into the src folders and it should be fine, as long as the file is labelled nicely.

## Github
I've set the github up so it won't let you push to main directly, so don't worry about breaking anything, just make sure you make your own branch then make a pull-request when you're done with your feature then we can merge it into main without interfering with each others' tasks and we always have a functional version of our work.

[Quick Git Refresher](https://www.youtube.com/watch?v=QV0kVNvkMxc)






