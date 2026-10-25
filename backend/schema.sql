IF DB_ID(N'MultiServiceDB') IS NULL
BEGIN
    CREATE DATABASE MultiServiceDB;
END;
GO

USE MultiServiceDB;
GO

IF OBJECT_ID(N'dbo.Users', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Users (
        UserID INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_Users PRIMARY KEY,
        FullName NVARCHAR(120) NOT NULL,
        Role VARCHAR(30) NOT NULL,
        Phone NVARCHAR(20) NOT NULL,
        Email NVARCHAR(254) NOT NULL,
        PasswordHash NVARCHAR(256) NULL,
        IsAdmin BIT NOT NULL CONSTRAINT DF_Users_IsAdmin DEFAULT 0,
        ApprovalStatus VARCHAR(20) NOT NULL CONSTRAINT DF_Users_ApprovalStatus DEFAULT 'APPROVED',
        State NVARCHAR(80) NOT NULL CONSTRAINT DF_Users_State DEFAULT N'Bihar',
        District NVARCHAR(80) NOT NULL CONSTRAINT DF_Users_District DEFAULT N'Siwan',
        ApprovalNote NVARCHAR(500) NULL,
        ApprovedAt DATETIME2(0) NULL,
        CreatedAt DATETIME2(0) NOT NULL CONSTRAINT DF_Users_CreatedAt DEFAULT SYSdatetime(),
        CONSTRAINT CK_Users_Role CHECK (Role IN ('buyer', 'seller_electronics', 'seller_medicine', 'advocate', 'admin')),
        CONSTRAINT CK_Users_IsAdminMatchesRole CHECK (
            (Role = 'admin' AND IsAdmin = 1) OR (Role <> 'admin' AND IsAdmin = 0)
        ),
        CONSTRAINT CK_Users_ApprovalStatus CHECK (ApprovalStatus IN ('PENDING', 'APPROVED', 'REJECTED')),
        CONSTRAINT UQ_Users_Phone UNIQUE (Phone),
        CONSTRAINT UQ_Users_Email UNIQUE (Email)
    );
END;
GO

IF COL_LENGTH(N'dbo.Users', N'PasswordHash') IS NULL
    ALTER TABLE dbo.Users ADD PasswordHash NVARCHAR(256) NULL;
IF COL_LENGTH(N'dbo.Users', N'IsAdmin') IS NULL
    ALTER TABLE dbo.Users ADD IsAdmin BIT NOT NULL
        CONSTRAINT DF_Users_IsAdmin DEFAULT 0 WITH VALUES;
IF COL_LENGTH(N'dbo.Users', N'ApprovalStatus') IS NULL
BEGIN
    ALTER TABLE dbo.Users ADD ApprovalStatus VARCHAR(20) NOT NULL
        CONSTRAINT DF_Users_ApprovalStatus DEFAULT 'APPROVED' WITH VALUES;
END;
IF COL_LENGTH(N'dbo.Users', N'ApprovalNote') IS NULL
    ALTER TABLE dbo.Users ADD ApprovalNote NVARCHAR(500) NULL;
IF COL_LENGTH(N'dbo.Users', N'ApprovedAt') IS NULL
    ALTER TABLE dbo.Users ADD ApprovedAt DATETIME2(0) NULL;
IF COL_LENGTH(N'dbo.Users', N'State') IS NULL
    ALTER TABLE dbo.Users ADD State NVARCHAR(80) NOT NULL CONSTRAINT DF_Users_State DEFAULT N'Bihar' WITH VALUES;
IF COL_LENGTH(N'dbo.Users', N'District') IS NULL
    ALTER TABLE dbo.Users ADD District NVARCHAR(80) NOT NULL CONSTRAINT DF_Users_District DEFAULT N'Siwan' WITH VALUES;
GO
IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = N'CK_Users_ApprovalStatus')
    ALTER TABLE dbo.Users ADD CONSTRAINT CK_Users_ApprovalStatus
        CHECK (ApprovalStatus IN ('PENDING', 'APPROVED', 'REJECTED'));
GO
UPDATE dbo.Users
SET IsAdmin = CASE WHEN Role = 'admin' THEN 1 ELSE 0 END
WHERE IsAdmin <> CASE WHEN Role = 'admin' THEN 1 ELSE 0 END;
GO
IF NOT EXISTS (
    SELECT 1 FROM sys.check_constraints
    WHERE parent_object_id = OBJECT_ID(N'dbo.Users')
      AND name = N'CK_Users_IsAdminMatchesRole'
)
    ALTER TABLE dbo.Users ADD CONSTRAINT CK_Users_IsAdminMatchesRole
        CHECK ((Role = 'admin' AND IsAdmin = 1) OR (Role <> 'admin' AND IsAdmin = 0));
GO

IF OBJECT_ID(N'dbo.Electronics', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Electronics (
        ItemID INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_Electronics PRIMARY KEY,
        SellerID INT NOT NULL,
        Title NVARCHAR(160) NOT NULL,
        Description NVARCHAR(MAX) NOT NULL,
        Category NVARCHAR(80) NOT NULL,
        Price DECIMAL(12,2) NOT NULL,
        SerialIMEI NVARCHAR(80) NULL,
        State NVARCHAR(80) NOT NULL CONSTRAINT DF_Electronics_State DEFAULT N'Bihar',
        District NVARCHAR(80) NOT NULL,
        ListingStatus VARCHAR(30) NOT NULL CONSTRAINT DF_Electronics_ListingStatus DEFAULT 'PENDING_VERIFICATION',
        CreatedAt DATETIME2(0) NOT NULL CONSTRAINT DF_Electronics_CreatedAt DEFAULT SYSdatetime(),
        CONSTRAINT FK_Electronics_Users FOREIGN KEY (SellerID) REFERENCES dbo.Users(UserID),
        CONSTRAINT CK_Electronics_Price CHECK (Price > 0),
        CONSTRAINT CK_Electronics_ListingStatus CHECK (ListingStatus IN ('PENDING_VERIFICATION', 'VERIFIED', 'SOLD'))
    );
    CREATE INDEX IX_Electronics_Category_Status ON dbo.Electronics(Category, ListingStatus);
END;
GO

IF COL_LENGTH(N'dbo.Electronics', N'State') IS NULL
    ALTER TABLE dbo.Electronics ADD State NVARCHAR(80) NOT NULL
        CONSTRAINT DF_Electronics_State DEFAULT N'Bihar' WITH VALUES;
GO

IF OBJECT_ID(N'dbo.ItemVerificationLogs', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.ItemVerificationLogs (
        LogID INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_ItemVerificationLogs PRIMARY KEY,
        ItemID INT NOT NULL,
        RecipientEmail NVARCHAR(254) NOT NULL,
        RecipientPhone NVARCHAR(20) NOT NULL,
        OTPCodeHash CHAR(64) NOT NULL,
        Channel VARCHAR(20) NOT NULL,
        EventType VARCHAR(30) NOT NULL,
        DispatchStatus VARCHAR(30) NOT NULL,
        VerificationStatus VARCHAR(20) NULL,
        AttemptNumber INT NOT NULL CONSTRAINT DF_ItemVerificationLogs_AttemptNumber DEFAULT 0,
        ExpiresAt DATETIME2(0) NOT NULL,
        AttemptedAt DATETIME2(0) NULL,
        VerificationTimestamp DATETIME2(0) NULL,
        CreatedAt DATETIME2(0) NOT NULL CONSTRAINT DF_ItemVerificationLogs_CreatedAt DEFAULT SYSdatetime(),
        CONSTRAINT FK_ItemVerificationLogs_Electronics FOREIGN KEY (ItemID) REFERENCES dbo.Electronics(ItemID),
        CONSTRAINT CK_ItemVerificationLogs_Channel CHECK (Channel IN ('EMAIL', 'WHATSAPP')),
        CONSTRAINT CK_ItemVerificationLogs_EventType CHECK (EventType IN ('DISPATCH', 'VERIFICATION_ATTEMPT')),
        CONSTRAINT CK_ItemVerificationLogs_AttemptNumber CHECK (AttemptNumber >= 0)
    );
    CREATE INDEX IX_ItemVerificationLogs_Item_Event ON dbo.ItemVerificationLogs(ItemID, EventType, Channel);
END;
GO

IF OBJECT_ID(N'dbo.Medicines', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Medicines (
        MedicineID INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_Medicines PRIMARY KEY,
        SellerID INT NOT NULL,
        Name NVARCHAR(160) NOT NULL,
        Description NVARCHAR(MAX) NOT NULL CONSTRAINT DF_Medicines_Description DEFAULT '',
        BatchNumber NVARCHAR(80) NOT NULL,
        Stock INT NOT NULL CONSTRAINT DF_Medicines_Stock DEFAULT 0,
        Price DECIMAL(10,2) NOT NULL,
        PrescriptionRequired BIT NOT NULL CONSTRAINT DF_Medicines_PrescriptionRequired DEFAULT 0,
        ChemistName NVARCHAR(120) NOT NULL,
        State NVARCHAR(80) NOT NULL CONSTRAINT DF_Medicines_State DEFAULT N'Bihar',
        District NVARCHAR(80) NOT NULL,
        CreatedAt DATETIME2(0) NOT NULL CONSTRAINT DF_Medicines_CreatedAt DEFAULT SYSdatetime(),
        CONSTRAINT FK_Medicines_Users FOREIGN KEY (SellerID) REFERENCES dbo.Users(UserID),
        CONSTRAINT CK_Medicines_Stock CHECK (Stock >= 0),
        CONSTRAINT CK_Medicines_Price CHECK (Price >= 0)
    );
    CREATE INDEX IX_Medicines_District_Name ON dbo.Medicines(District, Name);
END;
GO

IF COL_LENGTH(N'dbo.Medicines', N'State') IS NULL
    ALTER TABLE dbo.Medicines ADD State NVARCHAR(80) NOT NULL
        CONSTRAINT DF_Medicines_State DEFAULT N'Bihar' WITH VALUES;
GO

IF OBJECT_ID(N'dbo.PrescriptionOrders', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.PrescriptionOrders (
        OrderID INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_PrescriptionOrders PRIMARY KEY,
        MedicineID INT NOT NULL,
        CustomerName NVARCHAR(120) NOT NULL,
        CustomerPhone NVARCHAR(20) NOT NULL,
        CustomerEmail NVARCHAR(254) NOT NULL,
        Quantity INT NOT NULL,
        PrescriptionPath NVARCHAR(500) NULL,
        IsChronicRefill BIT NOT NULL CONSTRAINT DF_PrescriptionOrders_IsChronicRefill DEFAULT 0,
        RefillIntervalDays INT NULL,
        NextRefillAt DATETIME2(0) NULL,
        OrderStatus VARCHAR(20) NOT NULL CONSTRAINT DF_PrescriptionOrders_OrderStatus DEFAULT 'PLACED',
        CreatedAt DATETIME2(0) NOT NULL CONSTRAINT DF_PrescriptionOrders_CreatedAt DEFAULT SYSdatetime(),
        CONSTRAINT FK_PrescriptionOrders_Medicines FOREIGN KEY (MedicineID) REFERENCES dbo.Medicines(MedicineID),
        CONSTRAINT CK_PrescriptionOrders_Quantity CHECK (Quantity > 0),
        CONSTRAINT CK_PrescriptionOrders_RefillSchedule CHECK (
            (IsChronicRefill = 0 AND RefillIntervalDays IS NULL AND NextRefillAt IS NULL)
            OR
            (IsChronicRefill = 1 AND RefillIntervalDays IS NOT NULL AND RefillIntervalDays IN (30, 60, 90) AND NextRefillAt IS NOT NULL)
        ),
        CONSTRAINT CK_PrescriptionOrders_OrderStatus CHECK (OrderStatus IN ('PLACED', 'MATCHED', 'FULFILLED', 'CANCELLED'))
    );
    CREATE INDEX IX_PrescriptionOrders_Medicine_Status ON dbo.PrescriptionOrders(MedicineID, OrderStatus);
END;
GO

IF OBJECT_ID(N'dbo.Advocates', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Advocates (
        AdvocateID INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_Advocates PRIMARY KEY,
        UserID INT NULL,
        FullName NVARCHAR(120) NOT NULL,
        BarCouncilNumber NVARCHAR(80) NOT NULL,
        ExperienceYears INT NOT NULL,
        ConsultationFee DECIMAL(10,2) NOT NULL,
        Specialization NVARCHAR(80) NOT NULL,
        State NVARCHAR(80) NOT NULL CONSTRAINT DF_Advocates_State DEFAULT N'Bihar',
        District NVARCHAR(80) NOT NULL,
        Verified BIT NOT NULL CONSTRAINT DF_Advocates_Verified DEFAULT 0,
        CONSTRAINT FK_Advocates_Users FOREIGN KEY (UserID) REFERENCES dbo.Users(UserID),
        CONSTRAINT UQ_Advocates_BarCouncilNumber UNIQUE (BarCouncilNumber),
        CONSTRAINT CK_Advocates_ExperienceYears CHECK (ExperienceYears >= 0),
        CONSTRAINT CK_Advocates_ConsultationFee CHECK (ConsultationFee >= 0)
    );
    CREATE INDEX IX_Advocates_Specialization_Verified ON dbo.Advocates(Specialization, Verified);
END;
GO

IF COL_LENGTH(N'dbo.Advocates', N'State') IS NULL
    ALTER TABLE dbo.Advocates ADD State NVARCHAR(80) NOT NULL
        CONSTRAINT DF_Advocates_State DEFAULT N'Bihar' WITH VALUES;
GO

IF OBJECT_ID(N'dbo.Consultations', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Consultations (
        ConsultationID INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_Consultations PRIMARY KEY,
        AdvocateID INT NOT NULL,
        ClientName NVARCHAR(120) NOT NULL,
        ClientEmail NVARCHAR(254) NOT NULL,
        ClientPhone NVARCHAR(20) NOT NULL,
        SlotStart DATETIME2(0) NOT NULL,
        SlotEnd DATETIME2(0) NOT NULL,
        BookingStatus VARCHAR(20) NOT NULL CONSTRAINT DF_Consultations_BookingStatus DEFAULT 'BOOKED',
        CreatedAt DATETIME2(0) NOT NULL CONSTRAINT DF_Consultations_CreatedAt DEFAULT SYSdatetime(),
        CONSTRAINT FK_Consultations_Advocates FOREIGN KEY (AdvocateID) REFERENCES dbo.Advocates(AdvocateID),
        CONSTRAINT UQ_Consultations_AdvocateSlot UNIQUE (AdvocateID, SlotStart),
        CONSTRAINT CK_Consultations_BookingStatus CHECK (BookingStatus IN ('BOOKED', 'CANCELLED', 'COMPLETED')),
        CONSTRAINT CK_Consultations_Slot CHECK (SlotEnd > SlotStart)
    );
END;
GO

IF OBJECT_ID(N'dbo.ActivityLogs', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.ActivityLogs (
        ActivityID INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_ActivityLogs PRIMARY KEY,
        ActorUserID INT NULL,
        Action NVARCHAR(80) NOT NULL,
        TargetType NVARCHAR(40) NOT NULL,
        TargetID INT NULL,
        Description NVARCHAR(500) NOT NULL,
        CreatedAt DATETIME2(0) NOT NULL CONSTRAINT DF_ActivityLogs_CreatedAt DEFAULT SYSdatetime(),
        CONSTRAINT FK_ActivityLogs_Users FOREIGN KEY (ActorUserID) REFERENCES dbo.Users(UserID)
    );
    CREATE INDEX IX_ActivityLogs_Action ON dbo.ActivityLogs(Action);
    CREATE INDEX IX_ActivityLogs_CreatedAt ON dbo.ActivityLogs(CreatedAt);
END;
GO
