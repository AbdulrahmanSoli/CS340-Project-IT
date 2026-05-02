DROP TABLE IF EXISTS asset_status_history CASCADE;
DROP TABLE IF EXISTS asset_assignment CASCADE;
DROP TABLE IF EXISTS asset CASCADE;
DROP TABLE IF EXISTS employee CASCADE;
DROP TABLE IF EXISTS admin CASCADE;
DROP TABLE IF EXISTS users CASCADE;




CREATE TABLE users (
  userID INTEGER PRIMARY KEY,
  userFullName VARCHAR(100) NOT NULL,
  email TEXT UNIQUE NOT NULL,
  department VARCHAR(100),
  passwordHash VARCHAR(255) NOT NULL,
  createdDate DATE NOT NULL DEFAULT CURRENT_DATE,
  userType VARCHAR(20) NOT NULL,
  CONSTRAINT users_userType_check CHECK (userType IN ('Admin', 'Employee'))
);




CREATE TABLE admin (
  userID INTEGER PRIMARY KEY REFERENCES users(userID)
);




CREATE TABLE employee (
  userID INTEGER PRIMARY KEY REFERENCES users(userID)
);




CREATE TABLE asset (
  assetID INTEGER PRIMARY KEY,
  assetName VARCHAR(100) NOT NULL,
  category VARCHAR(100) NOT NULL,
  status VARCHAR(100) NOT NULL CHECK (status IN ('Available', 'Assigned', 'Damaged')),
  serialNum VARCHAR(100) UNIQUE NOT NULL,
  purchaseDate DATE,
  condition VARCHAR(100),
  notes TEXT
);




CREATE TABLE asset_assignment (
  assignmentID INTEGER PRIMARY KEY,
  assignedDate DATE NOT NULL,
  returnDate DATE,
  assetID INTEGER NOT NULL,
  userID INTEGER NOT NULL,
  assignedBy INTEGER,
  FOREIGN KEY (assetID) REFERENCES asset(assetID),
  FOREIGN KEY (userID) REFERENCES employee(userID),
  FOREIGN KEY (assignedBy) REFERENCES admin(userID),
  CONSTRAINT shouldntBeEarly CHECK (
    returnDate IS NULL OR returnDate >= assignedDate
  )
);


CREATE UNIQUE INDEX one_active_assignment_per_asset
  ON asset_assignment (assetID)
  WHERE returnDate IS NULL;




CREATE TABLE asset_status_history (
  historyID INTEGER PRIMARY KEY,
  previousStatus VARCHAR(100) NOT NULL CHECK (
    previousStatus IN ('Available', 'Assigned', 'Damaged')
  ),
  newStatus VARCHAR(100) NOT NULL CHECK (
    newStatus IN ('Available', 'Assigned', 'Damaged')
  ),
  changeDate DATE NOT NULL DEFAULT CURRENT_DATE,
  assetID INTEGER NOT NULL,
  changedBy INTEGER,
  FOREIGN KEY (assetID) REFERENCES asset(assetID),
  FOREIGN KEY (changedBy) REFERENCES admin(userID),
  CONSTRAINT status_changed CHECK (previousStatus <> newStatus)
);
