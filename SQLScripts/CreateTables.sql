USE JourneyDump;

CREATE TABLE Trains (
    Rid varchar(15) NOT NULL PRIMARY KEY,
);
GO

CREATE TABLE JourneyData (
    DataId int IDENTITY(1,1) NOT NULL PRIMARY KEY,

    Rid varchar(15) NOT NULL REFERENCES Trains(Rid),
    RelatedRid varchar(15),
    RecordType varchar(20),
    DataField1 varchar(4000),
    DataField2 varchar(4000),
    DataField3 varchar(4000),
    DataField varchar(4000)
);